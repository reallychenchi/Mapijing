#!/bin/bash

# Mapijing 自动化部署脚本
# 用于在 ai.chechi.cc 服务器上更新前端代码并构建发布

set -e

# 服务器配置
SERVER="root@ai.chenchi.cc"
PROJECT_DIR="/var/www/Mapijing"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=========================================="
echo "  Mapijing 自动化部署脚本"
echo "=========================================="
echo ""

# 1. 显示当前 git 状态
echo "[1/5] 检查本地代码变更..."
cd "$(dirname "$0")" || exit 1
git status --short
echo ""

# 2. 推送到远程仓库
echo "[2/5] 推送代码到远程仓库..."
git push origin master
echo ""

# 3. 在服务器上执行部署
echo "[3/5] 在服务器上拉取最新代码并构建..."
ssh "$SERVER" << 'EOF'
set -e

cd /var/www/Mapijing

echo "  - 拉取最新代码..."
git pull origin master

echo "  - 进入前端目录: /var/www/Mapijing/frontend"
cd /var/www/Mapijing/frontend

echo "  - 安装依赖 (npm install)..."
npm install

echo "  - 构建前端 (npm run build)..."
npm run build

echo "  - 重载 Nginx..."
nginx -s reload

echo "  - 部署完成!"
EOF

echo ""
echo "[4/5] 检查服务状态..."
ssh "$SERVER" "systemctl status nginx --no-pager | head -5"

echo ""
echo "[5/5] 部署完成！"
echo "=========================================="
echo "  前端已更新并发布到: http://ai.chechi.cc/mapijing/"
echo "=========================================="
