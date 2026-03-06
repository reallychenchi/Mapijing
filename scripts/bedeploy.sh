#!/bin/bash

# Mapijing 后端自动化部署脚本
# 用于在 ai.chenchi.cc 服务器上更新后端代码并重启服务

set -e

# 服务器配置
SERVER="root@ai.chenchi.cc"
PROJECT_DIR="/var/www/Mapijing"
BACKEND_DIR="$PROJECT_DIR/backend"

echo "=========================================="
echo "  Mapijing 后端自动化部署脚本"
echo "=========================================="
echo ""

# 1. 显示当前 git 状态
echo "[1/5] 检查本地代码变更..."
cd "$(dirname "$0")/.." || exit 1
git status --short
echo ""

# 2. 推送到远程仓库
echo "[2/5] 推送代码到远程仓库..."
git push origin master
echo ""

# 3. 在服务器上执行部署
echo "[3/5] 在服务器上拉取最新代码并安装依赖..."
ssh "$SERVER" << 'EOF'
set -e

cd /var/www/Mapijing

echo "  - 拉取最新代码..."
git pull origin master

echo "  - 进入后端目录: /var/www/Mapijing/backend"
cd /var/www/Mapijing/backend

echo "  - 安装依赖 (pip install -r requirements.txt)..."
pip install -r requirements.txt

echo "  - 重启后端服务..."
sudo systemctl restart mapijing.service

echo "  - 部署完成!"
EOF

echo ""
echo "[4/5] 检查服务状态..."
ssh "$SERVER" "systemctl status mapijing.service --no-pager | head -10"

echo ""
echo "[5/5] 部署完成！"
echo "=========================================="
echo "  后端服务已更新并重启: mapijing.service"
echo "=========================================="
