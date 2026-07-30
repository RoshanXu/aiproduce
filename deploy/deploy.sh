#!/bin/bash
# AIproduce 一键部署脚本
# 用法: bash deploy/deploy.sh

set -e

echo "=== AIproduce 云服务器部署 ==="

# 1. 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker 安装完成，请重新登录后再次运行此脚本"
    exit 0
fi

# 2. 检查 .env
if [ ! -f ".env" ]; then
    echo "未找到 .env 文件，从模板创建..."
    cp .env.example .env
    echo "请先编辑 .env 填入 API Key，再重新运行此脚本"
    echo "  nano .env"
    exit 1
fi

# 3. 构建镜像
echo "构建 Docker 镜像..."
docker build -t aiproduce .

# 4. 停止旧容器
docker rm -f aiproduce 2>/dev/null || true

# 5. 启动
echo "启动服务..."
docker run -d --name aiproduce \
    --restart unless-stopped \
    -p 7860:7860 \
    -v aiproduce_workspace:/app/workspace \
    -v $(pwd)/.env:/app/.env:ro \
    aiproduce

echo ""
echo "============================================"
echo "  部署完成!"
echo "  访问: http://$(curl -s ifconfig.me 2>/dev/null || echo '你的服务器IP'):7860"
echo ""
echo "  管理命令:"
echo "    docker logs -f aiproduce    查看日志"
echo "    docker restart aiproduce    重启服务"
echo "    docker stop aiproduce       停止服务"
echo "============================================"
