# Mapijing 项目部署指南 (Ubuntu 22.04)

## 项目技术栈

- **前端**: React + Vite + TypeScript
- **后端**: FastAPI + Uvicorn (Python)
- **反向代理**: Nginx

---

## 一、环境准备

### 1.1 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 安装必要软件

```bash
# 安装 Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 Python 3 和 pip
sudo apt install -y python3 python3-pip python3-venv

# 安装 Nginx
sudo apt install -y nginx

# 验证安装
node --version    # 应显示 v20.x.x
npm --version
python3 --version
nginx -v
```

### 1.3 配置防火墙

```bash
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (可选)
sudo ufw enable
```

---

## 二、部署步骤

### 2.1 创建项目目录

```bash
sudo mkdir -p /var/www/Mapijing
cd /var/www/Mapijing
```

### 2.2 上传代码

**方式一：使用 Git 克隆**
```bash
cd /var/www/Mapijing
sudo git clone <your-repo-url> .
```

**方式二：SFTP 上传**
将本地 `frontend`、`backend` 目录上传到 `/var/www/Mapijing/`

### 2.3 构建前端

```bash
cd /var/www/Mapijing/frontend
sudo npm install
sudo npm run build
```

构建产物位于 `/var/www/Mapijing/frontend/dist/`

### 2.4 安装后端依赖

```bash
cd /var/www/Mapijing/backend

# 创建虚拟环境
sudo python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 退出虚拟环境
deactivate
```

### 2.5 配置环境变量

```bash
cd /var/www/Mapijing/backend

# 创建 .env 文件，配置必要的环境变量
sudo nano .env
```

根据项目需求配置 API 密钥等敏感信息。

---

## 三、配置 Systemd 服务

### 3.1 创建服务文件

```bash
sudo nano /etc/systemd/system/mapijing.service
```

写入以下内容：

```ini
[Unit]
Description=Mapijing Backend API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/Mapijing/backend
Environment="PATH=/var/www/Mapijing/backend/venv/bin"
ExecStart=/var/www/Mapijing/backend/venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.2 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl start mapijing
sudo systemctl enable mapijing

# 检查服务状态
sudo systemctl status mapijing
```

---

## 四、配置 Nginx

### 4.1 创建配置文件

```bash
sudo nano /etc/nginx/sites-available/mapijing
```

写入以下内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或服务器 IP

    # 根路径重定向到 /mapijing
    location = / {
        return 301 /mapijing/;
    }

    # 前端静态文件
    location /mapijing/ {
        alias /var/www/Mapijing/frontend/dist/;
        index index.html;
        try_files $uri $uri/ /mapijing/index.html;
    }

    # 后端 API 代理
    location /mapijing/api/ {
        rewrite ^/mapijing/api/(.*)$ /$1 break;
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket 支持
    location /mapijing/ws/ {
        rewrite ^/mapijing/ws/(.*)$ /$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4.2 启用站点

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/mapijing /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

---

## 五、验证部署

### 5.1 检查服务状态

```bash
# 检查后端服务
sudo systemctl status mapijing

# 检查 Nginx
sudo systemctl status nginx
```

### 5.2 访问应用

- 打开浏览器访问：`http://your-server/mapijing`
- 根路径会自动重定向到 `/mapijing/`

### 5.3 查看日志

```bash
# 后端日志
sudo journalctl -u mapijing -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
```

---

## 六、常用命令

| 操作 | 命令 |
|------|------|
| 启动后端 | `sudo systemctl start mapijing` |
| 停止后端 | `sudo systemctl stop mapijing` |
| 重启后端 | `sudo systemctl restart mapijing` |
| 重载 Nginx | `sudo systemctl reload nginx` |
| 重启 Nginx | `sudo systemctl restart nginx` |
| 查看后端日志 | `sudo journalctl -u mapijing -f` |

---

## 七、更新部署

当代码更新时，执行以下步骤：

```bash
# 1. 进入项目目录
cd /var/www/Mapijing

# 2. 拉取最新代码
sudo git pull

# 3. 重新构建前端
cd frontend
sudo npm install
sudo npm run build

# 4. 重启后端服务
sudo systemctl restart mapijing
```

---

## 八、（可选）配置 HTTPS

### 8.1 安装 Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 8.2 获取 SSL 证书

```bash
sudo certbot --nginx -d your-domain.com
```

按照提示完成配置，Certbot 会自动修改 Nginx 配置并启用 HTTPS。

### 8.3 自动续期

```bash
sudo certbot renew --dry-run
```

Certbot 会自动安装续期任务。
