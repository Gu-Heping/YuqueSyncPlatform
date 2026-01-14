# YuqueSyncPlatform 技术交接文档

## 1. 项目概述
YuqueSyncPlatform 是一个基于语雀 API 的文档同步、展示、搜索与团队协作增强平台。它不仅同步语雀的知识库文档，还提供了基于向量数据库（RAG）的 AI 问答、本地化的评论系统、团队动态流（Feed）以及邮件通知功能。

## 2. 技术栈架构

### 2.1 后端 (Backend)
*   **框架**: FastAPI (Python 3.8+) - 异步高性能 Web 框架。
*   **数据库 ORM**: Beanie - 基于 Motor 的 MongoDB 异步 ODM。
*   **依赖管理**: `requirements.txt` / pip。
*   **核心库**:
    *   `httpx`: 异步 HTTP 请求（调用语雀 API）。
    *   `pydantic-settings`: 环境变量管理。
    *   `qdrant-client`: 向量数据库客户端。
    *   `openai`: AI 接口调用（兼容 OpenAI 协议）。

### 2.2 前端 (Frontend)
*   **框架**: React 18。
*   **构建工具**: Vite (推测，基于项目结构)。
*   **UI 框架**: Tailwind CSS。
*   **路由**: React Router DOM。
*   **状态管理**: React Context (`AuthContext`, `ThemeContext`).
*   **HTTP 客户端**: Axios (`api.js` 统一封装拦截器)。
*   **图标库**: Lucide React.
*   **服务器**: Nginx (Docker 容器内用于托管静态资源反向代理)。

### 2.3 基础设施 & 数据存储
*   **应用容器化**: Docker & Docker Compose。
*   **主数据库**: MongoDB (存储文档元数据、用户信息、评论、动态)。
*   **向量数据库**: Qdrant (存储文档 Embedding，用于 RAG 搜索)。
*   **部署模式**: 支持单机多实例部署（通过 `HOST_PORT` 环境变量隔离端口）。

---

## 3. 核心业务逻辑与代码结构

### 3.1 目录结构说明
```bash
/app
  /api          # API 路由 (v1 endpoints)
    auth.py     # 用户认证/个人信息修改
    comments.py # 评论获取与状态检查
    members.py  # 成员管理 (关注、统计、关注逻辑)
    ...
  /core         # 核心配置
    config.py   # Settings 类，读取 .env
  /models       # 数据库模型 (Beanie Document)
    schemas.py  # User, Member, Doc, Comment, Activity 定义
  /services     # 业务逻辑层 (重逻辑)
    feed_service.py    # 生成动态流，逻辑修正：优先使用 actor_id
    comment_service.py # 评论处理，嵌套结构，邮件通知
    email_service.py   # SMTP 邮件发送，HTML 模板渲染
    webhook_service.py # 语雀 Webhook 分发入口
/frontend       # React 源码
  /src/components # UI 组件 (Layout, CommentSection, MessageList)
  /src/pages      # 页面级组件
```

### 3.2 关键数据模型 (Schema)
*   **Member (members)**: `yuque_id` (Index), `email`, `followers` (List[int]), `last_read_*`。
*   **Doc (docs)**: 文档元数据，`body_html`，`embedding_status`。
*   **Comment (comments)**: `yuque_id`, `parent_id` (用于递归树形结构), `body_html`。
*   **Activity (activity)**: 动态流，字段 `actor_id` (操作者) 与 `user_id` (所属者) 区分明确。

### 3.3 核心流程逻辑

#### A. Webhook 同步流程
1.  **入口**: `POST /api/v1/webhook`。
2.  **分发**: `WebhookService` 根据 `action_type` 分发。
3.  **处理**:
    *   **文档更新**: 更新 MongoDB -> 触发 Embedding (写入 Qdrant) -> 生成 `update` 动态。
    *   **评论创建**: 写入 `Comment` 表 -> `FeedService` 生成动态 -> `EmailService` 发送邮件通知被评论人。

#### B. 评论系统
*   **前端**: `CommentSection.jsx` 使用递归组件渲染树形评论（支持 `parent_id`）。
*   **后端**: 保存评论时保留 `body_html`。
*   **通知**: `handle_notification` 逻辑中构造文档链接 `/repos/{repo_id}/docs/{doc_slug}`。

#### C. 邮件通知
*   使用 SMTP 发送 HTML 邮件。
*   **路径修正**: 链接包含完整的 `repo_id` 路径以匹配前端路由。

---

## 4. 近期重要变更与修复 (Context for AI)

接手的 AI 请务必注意以下已实施的修复，**不要回滚**：

1.  **移动端适配 (Layout.jsx / MessageList.jsx)**:
    *   `Layout.jsx`: Header 按钮在移动端隐藏文字或隐藏 GitHub 图标，防止溢出。
    *   `MessageList.jsx`: 使用 `flex-wrap` 和 `break-all` 修复多行文字错位；时间显示垂直排列。

2.  **时间格式化**:
    *   前端统一使用 `formatDate` 工具函数。
    *   强制显示为 "YYYY/MM/DD HH:mm:ss" 格式，修正 UTC 时间直接显示导致的 8 小时时差问题。

3.  **API 逻辑准确性**:
    *   `api/members.py`: 统计绑定邮箱数时，使用 `{"$ne": None}` 查询并在内存中过滤空字符串 (`strip()`)，确保数据准确。
    *   `api/auth.py`: 绑定邮箱接口允许接收 `""` 或 `None` 以解绑邮箱。

4.  **Feed 归属权**:
    *   `FeedService`: 生成动态时，`author` 信息优先取 `payload.actor` (操作者)，而非 `payload.user` (资源归属者，可能是团队)。

5.  **部署配置**:
    *   `docker-compose.prod.yml`: 端口映射改为 `"${HOST_PORT:-80}:80"`，支持通过环境变量部署多套实例而不冲突。

---

## 5. 部署与环境

### 5.1 环境变量 (.env)
必须配置：
*   `YUQUE_TOKEN`: 语雀访问令牌。
*   `MONGO_URI`: MongoDB 连接串。
*   `HOST_PORT`: (可选) 宿主机暴露端口，默认 80。
*   `FRONTEND_URL`: 前端访问地址 (用于邮件内跳转)。

### 5.2 启动命令
```bash
# 正常启动
docker-compose -f docker-compose.prod.yml up -d

# 指定端口启动 (多实例模式)
# Windows PowerShell
$env:HOST_PORT="81"; docker-compose -f docker-compose.prod.yml up -d
```

## 6. 待优化/建议方向
1.  **Redis 缓存**: 目前 `Member` 等信息频繁查询数据库，可引入 Redis。
2.  **任务队列**: 邮件发送目前使用 FastAPI `BackgroundTasks`，高并发下建议迁移至 Celery。
3.  **Embedding 优化**: 当前向量化是同步或简单异步，大文档更新可能阻塞，建议完全解耦。
