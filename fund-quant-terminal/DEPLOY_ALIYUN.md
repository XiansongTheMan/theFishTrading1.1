# 阿里云服务器部署指南 - Fund Quant Terminal

本文档说明如何将 fund-quant-terminal 部署到阿里云 ECS 服务器。

---

## 一、前置准备

### 1. 阿里云 ECS

- 推荐配置：2核4G 及以上（若数据量小，1核2G 也可）
- 系统：Ubuntu 22.04 LTS 或 CentOS 7+
- 安全组需开放：22 (SSH)、80 (HTTP)、443 (HTTPS)

### 2. 域名（可选）

若有域名，可在阿里云解析到 ECS 公网 IP，便于使用 HTTPS。

---

## 二、服务器环境安装

### 1. 安装 Docker 与 Docker Compose

**Ubuntu：**

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

### 2. 安装 Nginx

```bash
sudo apt install -y nginx
```

---

## 三、本地构建前端

```bash
cd fund-quant-terminal/frontend

# 使用 Nginx 反向代理时设为 /api，请求会走同源
export VITE_API_BASE=/api
npm run build
```

生成 `dist/` 目录。

---

## 四、上传到服务器

```bash
scp -r fund-quant-terminal root@你的服务器IP:/opt/
```

---

## 五、服务器配置

### 1. 配置 .env

```bash
cd /opt/fund-quant-terminal
cp .env.example .env
nano .env
```

修改 CORS 为实际访问地址：

```env
CORS_ORIGINS=http://你的服务器IP,http://你的域名
```

### 2. 启动 MongoDB + 后端

```bash
cd /opt/fund-quant-terminal
docker compose up -d
```

### 3. 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/fund-quant
```

内容：

```nginx
server {
    listen 80;
    server_name 你的IP或域名;
    root /opt/fund-quant-terminal/frontend/dist;
    index index.html;
    try_files $uri $uri/ /index.html;
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/fund-quant /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 六、访问验证

浏览器访问 `http://你的服务器IP` 即可使用。

---

## 七、常见问题

- **CORS 报错**：在 .env 的 CORS_ORIGINS 中加入前端访问地址
- **API 404**：检查 Nginx 的 proxy_pass 是否为 http://127.0.0.1:8000
- **防火墙**：`sudo ufw allow 80 && sudo ufw enable`
