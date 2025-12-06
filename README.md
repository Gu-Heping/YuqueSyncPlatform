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

## 🐳 部署建议

推荐使用 Docker Compose 进行全栈部署。

### 架构示意
`Nginx (Gateway)` -> `/api/*` -> `FastAPI Container`
`Nginx (Gateway)` -> `/*` -> `React Static Files`

详细部署配置请参考项目文档中的 `docker-compose.prod.yml`。

---

## 📄 License

MIT License © 2025 YuqueSyncPlatform
