#!/bin/bash

# Manus AI Agent 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Manus AI Agent ===${NC}"
echo ""

# 检查Python环境
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    if [ -f "env.template" ]; then
        echo -e "${YELLOW}Creating .env from template...${NC}"
        cp env.template .env
        echo -e "${RED}Please edit .env file with your API keys${NC}"
    fi
fi

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 设置工作区路径
export WORKSPACE_PATH="$PROJECT_ROOT"

# 解析参数
MODE="dev"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            MODE="prod"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --build-frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# 构建前端 (如果需要)
if [ "$BUILD_FRONTEND" = true ] || [ "$MODE" = "prod" ]; then
    if [ -d "frontend" ]; then
        echo -e "${GREEN}Building frontend...${NC}"
        cd frontend
        
        if [ ! -d "node_modules" ]; then
            npm install
        fi
        
        npm run build
        cd ..
        echo -e "${GREEN}Frontend built successfully${NC}"
    fi
fi

# 启动服务
echo ""
echo -e "${GREEN}Starting Manus AI Agent...${NC}"
echo -e "Mode: ${YELLOW}$MODE${NC}"
echo -e "Host: ${YELLOW}$HOST${NC}"
echo -e "Port: ${YELLOW}$PORT${NC}"
echo ""

if [ "$MODE" = "prod" ]; then
    # 生产模式
    uvicorn src.api.main:app --host "$HOST" --port "$PORT" --workers 4
else
    # 开发模式
    uvicorn src.api.main:app --host "$HOST" --port "$PORT" --reload
fi

