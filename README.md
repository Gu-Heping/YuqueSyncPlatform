# 📚 YuqueSyncPlatform (语雀知识库同步与 RAG 平台)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-18.2-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)

这是一个集成了 **语雀文档同步**、**混合检索 (Hybrid Search)** 和 **RAG 智能问答** 的现代化知识库平台。它能够将语雀知识库自动同步到本地 MongoDB，并利用 Qdrant 向量数据库实现基于语义的智能搜索与问答。

---

## ✨ 核心功能

### 1. 🔄 全量与增量同步
- **自动同步**: 支持同步语雀知识库的文档、目录结构 (TOC) 和团队成员信息。
- **Webhook 集成**: 实时响应语雀 Webhook 事件（发布、更新、删除），毫秒级更新本地数据。
- **数据完整性**: 智能处理目录树重构，自动清理过期文档 (Pruning)，确保本地数据与语雀完全一致。

### 2. 🔍 混合检索 (Hybrid Search)
- **双路召回**: 结合 MongoDB 的 **全文检索 (BM25)** 和 Qdrant 的 **向量检索 (Embedding)**。
- **RRF 融合**: 使用倒数排名融合 (Reciprocal Rank Fusion) 算法，兼顾“精确关键词匹配”和“语义模糊匹配”。
- **高亮摘要**: 搜索结果包含关键词高亮和语义相关的片段摘要。

### 3. 🤖 AI 智能助手 (RAG)
- **上下文对话**: 支持多轮对话，AI 能理解“这个”、“上一篇”等指代词。
- **数据增强**: 检索时自动注入文档的作者、更新时间等元数据，增加回答的可信度。
- **Markdown 渲染**: 完美支持代码块高亮、表格和数学公式渲染。

### 4. 📊 现代化前端
- **响应式设计**: 基于 React + Tailwind CSS，完美适配桌面端和移动端。
- **沉浸式体验**: 类似 IDE 的文档阅读体验，支持侧边栏导航和悬浮目录。
- **移动端优化**: 手机端支持全屏阅读和抽屉式导航。

---

## 🛠️ 技术栈

- **Backend**: Python, FastAPI, Beanie (MongoDB ODM)
- **Database**: MongoDB (Metadata/Docs), Qdrant (Vector Store)
- **AI/LLM**: LangChain, OpenAI API (GPT-4/3.5), OpenAI Embeddings
- **Frontend**: React, Vite, Tailwind CSS, Lucide React, React Markdown

---

## 🚀 快速开始 (Local Dev)

### 前置要求
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### 1. 启动数据库
使用 Docker Compose 启动 MongoDB 和 Qdrant：
```bash
docker-compose up -d
```

### 2. 后端启动
```bash
cd app
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境 (Windows)
.\.venv\Scripts\Activate.ps1
# 安装依赖
pip install -r requirements.txt
# 配置环境变量 (参考下方)
cp .env.example .env
# 启动服务
uvicorn app.main:app --reload
```

### 3. 前端启动
```bash
cd frontend
# 安装依赖
npm install
# 启动开发服务器
npm run dev
```

访问 `http://localhost:5173` 即可看到应用界面。API 文档位于 `http://localhost:8000/docs`。

---

## ⚙️ 环境变量 (.env)

在项目根目录创建 `.env` 文件：

```ini
# MongoDB 配置
MONGO_URI=mongodb://admin:password@localhost:27017
MONGO_DB_NAME=yuque_db

# Qdrant 配置
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=yuque_docs

# 语雀配置 (用于同步)
YUQUE_TOKEN=your_yuque_access_token
YUQUE_BASE_URL=https://www.yuque.com/api/v2

# OpenAI 配置 (用于 RAG)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 🐳 全栈部署 (Docker Compose)

本项目提供了开箱即用的 Docker Compose 配置，支持一键部署完整环境（前端 + 后端 + 数据库）。

### 1. 配置环境变量
在服务器项目根目录创建 `.env` 文件，填入必要的 API Key 和 Token：

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件
vim .env
```
确保填入以下关键信息：
- `YUQUE_TOKEN`: 您的语雀 Token
- `OPENAI_API_KEY`: OpenAI API Key (用于 RAG)

### 2. 启动服务
使用 `docker-compose.prod.yml` 启动生产环境：

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

该命令会自动：
1. 构建前端 React 应用 (Build Stage) 并打包进 Nginx 容器。
2. 构建后端 FastAPI 应用容器。
3. 启动 MongoDB 和 Qdrant 数据库容器。
4. 自动配置 Nginx 反向代理 (前端端口 80 -> 后端端口 8000)。

### 3. 验证部署
- **前端访问**: `http://your-server-ip`
- **API 文档**: `http://your-server-ip/api/docs` (注意 Nginx 配置了 `/api` 前缀转发)

### 4. 常用运维命令
```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 更新代码后重新部署
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## ❓ 常见问题 (FAQ)

### Q: Docker 构建失败，提示 `failed to fetch anonymous token` 或 `dial tcp ... timeout`?
这是由于网络无法连接到 Docker Hub。请配置 Docker 镜像加速器。

**解决方案 (Docker Desktop):**
1. 打开 Docker Desktop 设置 -> **Docker Engine**。
2. 修改配置 JSON，添加 `registry-mirrors`：
   ```json
   {
     "builder": {
       "gc": {
         "defaultKeepStorage": "20GB",
         "enabled": true
       }
     },
     "experimental": false,
     "registry-mirrors": [
       "https://docker.m.daocloud.io",
       "https://huecker.io",
       "https://mirror.ccs.tencentyun.com"
     ]
   }
   ```
3. 点击 **Apply & restart** 重启 Docker。

---

## 📄 License

MIT License © 2025 YuqueSyncPlatform
