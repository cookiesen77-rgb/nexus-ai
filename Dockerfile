# Manus AI Agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Node.js (用于前端构建)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器
RUN pip install playwright && playwright install chromium --with-deps

# 复制源代码
COPY src/ ./src/
COPY config/ ./config/
COPY config.yaml .
COPY scripts/ ./scripts/

# 构建前端
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app

# 创建数据目录
RUN mkdir -p /app/data /app/logs /workspace

# 环境变量
ENV PYTHONPATH=/app
ENV WORKSPACE_PATH=/workspace

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
