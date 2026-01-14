# 多实例部署指南 (基于目录隔离)

本指南介绍如何通过**复制项目目录**的方式在同一台服务器上部署多个 YuqueSyncPlatform 实例。
**适用场景**：你需要为不同的团队运行独立的实例，并且未来可能针对不同团队修改代码或扩展功能。

---

## 核心思路

每个实例拥有独立的文件夹。通过不同的文件夹区分不同的团队（如 `yuque-sync-team-a`, `yuque-sync-team-b`）。每个文件夹内有独立的配置文件 (`.env`) 和代码。

---

## 操作步骤

我们将以创建第二个实例（Team B）为例。假设当前项目在一个名为 `YuqueSyncPlatform` 的目录中。

### 1. 复制/克隆项目

在服务器上，将现有项目复制到一个新目录，或者重新 git clone 一份。

**方法 A: 复制现有目录 (推荐，如果已有修改)**
```bash
# 回到上级目录
cd ..

# 复制项目到新文件夹 (例如 YuqueSyncPlatform_TeamB)
cp -r YuqueSyncPlatform YuqueSyncPlatform_TeamB

# 进入新目录
cd YuqueSyncPlatform_TeamB
```

**方法 B: 重新 Clone**
```bash
git clone https://github.com/your/repo.git YuqueSyncPlatform_TeamB
cd YuqueSyncPlatform_TeamB
```

### 2. 修改配置 (.env)

进入新目录 (`YuqueSyncPlatform_TeamB`) 后，编辑 `.env` 文件。这是**最关键**的一步，必须确保端口不冲突。

打开 `.env` 文件：

```bash
# 修改以下关键项

# 1. 宿主机端口 (CRITICAL)
# 必须改为一个未被使用的端口，例如 81 (原实例通常是 80)
HOST_PORT=81

# 2. 语雀 Token
YUQUE_TOKEN=your_token_for_team_b

# 3. 数据库名称 (可选，建议修改以示区分)
# 虽然容器是隔离的，但改名有助于在 MongoDB 客户端连接时区分
MONGO_DB_NAME=yuque_db_team_b

# 4. 前端地址 (用于邮件跳转)
# 对应修改后的宿主机端口
FRONTEND_URL=http://your-server-ip:81
```

### 3. 清理旧构建/缓存 (仅限复制方式)

如果你是直接复制的文件夹，建议先停止并清理可能残留的旧容器配置（虽然 docker-compose 默认会根据目录名隔离，但为了保险起见）：

```bash
# 确保没有旧的容器在运行 (在新目录下执行)
docker-compose -f docker-compose.prod.yml down
```

### 4. 启动新实例

在新目录下启动服务。Docker Compose 会默认使用当前目录名作为 Project Name，从而自动隔离容器和网络。

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5. 验证

查看运行中的容器：
```bash
docker ps
```
你应该能看到两组容器，分别对应不同的端口（例如 0.0.0.0:80 和 0.0.0.0:81）。

---

## Webhook 配置

在语雀后台为 Team B 配置 Webhook 时，使用新端口：

*   **Webhook URL**: `http://<服务器IP>:81/api/v1/webhook/yuque`

---

## 优缺点分析

*   **优点**：
    *   **完全隔离**：代码、配置、日志完全物理分离。
    *   **独立扩展**：你可以随意修改 Team B 的代码（例如添加定制功能），而不影响 Team A。
    *   **操作简单**：不需要额外的 `-p` 参数，进入对应目录操作即可。
*   **缺点**：
    *   **占用空间**：多份代码和虚拟环境会占用更多磁盘空间。
    *   **维护成本**：如果核心代码更新，需要分别去两个目录 `git pull`。
