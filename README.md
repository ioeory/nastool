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

本项目推荐使用 Docker Compose 部署。**请克隆完整仓库后在项目根目录执行 Compose**，以便构建上下文包含 `app/`、`config/` 等目录（不要只下载单独的 `docker-compose.yml`，否则无法构建后端镜像）。

### 1. 获取代码与环境文件

```bash
git clone <你的仓库地址> nastool && cd nastool
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env`，按需修改。常用项：

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | JWT 密钥，务必改为足够长的随机字符串 |
| `SUPERUSER` / `SUPERUSER_PASSWORD` | 首次启动创建的超级管理员 |
| `DOWNLOAD_PATH` / `LIBRARY_PATH` | 宿主机下载目录与媒体库目录（挂载到容器内） |

可选 Docker **构建**参数（减小镜像体积时保持默认即可）：

| 变量 | 说明 |
|------|------|
| `WITH_PLAYWRIGHT_BROWSER` | 默认 `0`。仅在需要 Playwright/Chromium（如部分站点浏览器绕过）时设为 `1`，会显著增大后端镜像 |

### 3. 启动服务

```bash
docker compose up -d
```

启动完成后访问 `http://<主机 IP>:3000` 进入 Web UI，账号密码见 `.env` 中的 `SUPERUSER` / `SUPERUSER_PASSWORD`。

### 4. 常见问题

**后端日志提示 `Could not import module "app.main"`**

- 若在 Compose 里把宿主机 **空的或不完整的 `./app`** 挂载到容器内 **`/app/app`**，会覆盖镜像内的代码导致导入失败。默认提供的 `docker-compose.yml` **不应**挂载后端源码目录；需要改代码热重载时请使用下文「后端开发（Docker）」中的 **`docker-compose.dev.yml`**。
- 修改 Compose 或 `.env` 后执行：`docker compose up -d --build`，确保使用最新构建参数。

## 🛠 开发指南

### 后端开发（本地）

后端基于 FastAPI + Python 3.11。

```bash
python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -e ".[dev]"

uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

### 后端开发（Docker，热重载）

使用开发覆盖配置，挂载后端 `app/` 并以 `--reload` 启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 前端开发

前端基于 Vue 3 + Vite。

```bash
cd frontend
npm install
npm run dev
```

单独开发前端时，请将 API 指向本地后端（例如 Vite 代理或环境变量中的后端地址）。

## 🐳 Docker 镜像与 CI

### GitHub Actions（GHCR）

推送到 `main` / `master`（且变更命中工作流路径过滤）时，会自动构建并推送镜像到 **GitHub Container Registry**：

- `ghcr.io/<owner>/<repo>-backend:latest`（及分支名、`sha` 等标签）
- `ghcr.io/<owner>/<repo>-frontend:latest`

流水线在推送前会对镜像做**冒烟测试**（例如后端镜像内执行 `import app.main`，前端检查静态文件），失败则不会推送，降低「坏镜像」流入 registry 的概率。

### 镜像体积说明

- 默认 **`WITH_PLAYWRIGHT_BROWSER=0`**：不在镜像内安装 Playwright 浏览器组件，镜像更小。
- 若业务依赖浏览器自动化，构建时传入 `WITH_PLAYWRIGHT_BROWSER=1`（见 `.env.example` 与 `docker-compose.yml` 中的 `build.args`）。

本地手动构建示例：

```bash
docker compose build --build-arg WITH_PLAYWRIGHT_BROWSER=1 backend
```

## 📝 许可证 (License)

[GPL-3.0 License](./LICENSE)
