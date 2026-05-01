# NasTool

NasTool 是一款 NAS 媒体库自动化管理工具，旨在自动化处理媒体库的订阅、下载、刮削和整理，提供一站式的家庭观影自动化解决方案。

> **免责声明与协议说明**
>
> 1. **GPL-3.0 协议**: 本项目基于开源项目 [MoviePilot](https://github.com/jxxghp/MoviePilot) 修改并重构而来。遵循原项目的 **GNU General Public License v3.0 (GPL-3.0)** 协议开源。任何对本项目的分发和修改都必须同样遵循 GPL-3.0 协议并开源。
> 2. **仅供学习交流**: 本软件仅供学习和交流使用，任何人不得将其用于商业用途或任何非法活动。使用者自行承担使用本软件所带来的一切风险和责任。

## ✨ 特性

- **前后端分离架构**: 后端基于 FastAPI，前端基于 Vue3 + Element Plus 构建，响应快速，体验流畅。
- **站点与刷流 (PT)**: 自动化 PT 刷流、站点自动签到。
- **媒体管理**: 强大的媒体文件监控、自动整理、重命名及刮削归档功能。
- **智能订阅**: 根据规则自动化订阅剧集和电影。
- **多客户端支持**: 完美支持主流下载器 (qBittorrent, Transmission) 和媒体服务器 (Emby, Jellyfin, Plex)。
- **消息推送**: 支持通过 Telegram、企业微信等渠道实时发送通知。

## 🚀 快速开始

本项目推荐使用 Docker Compose 进行部署。

### 1. 准备目录与文件

在你的宿主机（如 NAS 或 Linux 服务器）上创建一个项目目录并进入：

```bash
mkdir -p nastool && cd nastool
```

下载 `docker-compose.yml` 和 `.env.example`，并将 `.env.example` 重命名为 `.env`：

```bash
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，根据你的实际环境进行配置。最关键的配置项包括：

- `SECRET_KEY`: 请务必修改为一个随机字符串（用于 JWT 加密）。
- `SUPERUSER` / `SUPERUSER_PASSWORD`: 设置初始管理员账号密码。
- 目录挂载路径: `DOWNLOAD_PATH`（下载器目录）和 `LIBRARY_PATH`（最终媒体库整理目录）。

### 3. 启动服务

使用 Docker Compose 一键启动：

```bash
docker-compose up -d
```

启动完成后，通过浏览器访问 `http://<你的IP>:3000` 即可进入 NasTool Web UI。默认账号和密码由 `.env` 文件中的 `SUPERUSER` 和 `SUPERUSER_PASSWORD` 指定。

## 🛠 开发指南

### 后端开发

后端基于 FastAPI + Python 3.11。

```bash
# 建议使用虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -e .[dev]

# 运行后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

### 前端开发

前端基于 Vue 3 + Vite。

```bash
cd frontend

# 安装依赖
npm install

# 运行前端
npm run dev
```

## 🐳 Docker 自动构建

本项目已配置 GitHub Actions。在每次向 `main` 分支推送非文档类代码更新时，将会自动构建最新的 Docker 镜像，并推送到 GitHub Container Registry (GHCR)。

- 后端镜像: `ghcr.io/<你的用户名>/<仓库名>-backend:latest`
- 前端镜像: `ghcr.io/<你的用户名>/<仓库名>-frontend:latest`

## 📝 许可证 (License)

[GPL-3.0 License](./LICENSE)
