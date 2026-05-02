# ============================================================
# 后端 Dockerfile
# 多阶段构建：builder 安装依赖，runner 最小化运行时
#
# 可选组件 Playwright + Chromium 体积极大（常 400MB+），默认不安装。
# 需要站点浏览器绕过（Cloudflare 等）时使用：
#   docker build --build-arg WITH_PLAYWRIGHT_BROWSER=1 -f Dockerfile ./backend
# ============================================================

# ---- 阶段1：安装依赖 ----
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# 编译依赖（仅在 builder，不进最终镜像）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# 默认排除 playwright 包；启用浏览器时再安装（见下方 ARG）
ARG WITH_PLAYWRIGHT_BROWSER=0

RUN mkdir -p /root/.cache/ms-playwright \
    && grep -vE '^[[:space:]]*playwright' requirements.txt > /tmp/requirements.no_pw.txt \
    && pip install --upgrade pip \
    && pip install --user --no-cache-dir -r /tmp/requirements.no_pw.txt \
    && rm /tmp/requirements.no_pw.txt \
    && if [ "$WITH_PLAYWRIGHT_BROWSER" = "1" ]; then \
         pip install --user --no-cache-dir "playwright>=1.35.0" \
         && python -m playwright install chromium; \
       fi

# ---- 阶段2：运行时 ----
FROM python:3.11-slim-bookworm AS runner

LABEL maintainer="nastool"
LABEL description="NAS 媒体库自动化管理工具 — 后端"

ARG WITH_PLAYWRIGHT_BROWSER=0

# 系统运行时依赖（libxml/libxslt：站点解析；curl：健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 nastool

WORKDIR /app

COPY --from=builder /root/.local /home/nastool/.local
COPY --from=builder /root/.cache/ms-playwright /home/nastool/.cache/ms-playwright

COPY --chown=nastool:nastool app/ ./app/

RUN mkdir -p /data/db /data/logs /data/config \
    && chown -R nastool:nastool /data /home/nastool/.local /home/nastool/.cache

# 浏览器启用时：安装 Chromium 动态链接所需系统库（与 builder 阶段分离，单层 apt）
RUN if [ "$WITH_PLAYWRIGHT_BROWSER" = "1" ]; then \
      apt-get update \
      && PYTHONPATH="/home/nastool/.local/lib/python3.11/site-packages" \
         python3 -m playwright install-deps chromium \
      && rm -rf /var/lib/apt/lists/*; \
    fi

USER nastool

ENV PATH=/home/nastool/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:3001/api/v1/system/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "3001", \
     "--workers", "1"]
