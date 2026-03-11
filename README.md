# Fund Quant Terminal - 基金量化终端

生产级基金量化终端，支持 AKShare/Tushare 数据、决策日志、资产曲线。默认使用 Qwen 大模型，支持 Grok 等可选模型（通过配置切换）。

---

## 一、启动步骤

### 1. 启动 MongoDB

```bash
docker compose up -d
```

MongoDB 运行在 `localhost:27017`。后端启动时会自动创建索引。

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 或 run.bat / run.sh 会自动复制
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

或使用启动脚本：

- Windows: `run.bat`
- Linux/macOS: `./run.sh`

启动时自动创建 MongoDB 索引。接口: http://localhost:8000，Swagger: http://localhost:8000/docs  

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端: http://localhost:5173，每 60 秒自动刷新资产数据。

---

## 二、如何使用 AKShare / Tushare

### AKShare（免 Token）

- 数据终端：输入基金代码（如 `000001`），点击「拉取净值」获取净值数据  
- 基金列表、股票日线、指数日线均通过 AKShare 拉取  

### Tushare（需 Token）

1. 在 [tushare.pro](https://tushare.pro) 注册并获取 Token  
2. 将 Token 写入 `backend/.env`：`TUSHARE_TOKEN=你的token`  
3. 数据终端选择 `data_type=info` 时调用 Tushare 基金信息接口  

### 主要数据接口

| 接口 | 说明 |
|------|------|
| POST `/api/data/fetch` | 拉取基金净值(nav)、基金列表(list)、Tushare 信息(info) |
| GET `/api/data/history` | 基金净值历史，支持日期和条数限制 |
| POST `/api/analyze-portfolio` | 一键 AI 分析：聚合资产、新闻、市场快照，返回投资建议（默认 Qwen） |

---


---

## 五、项目结构

```
fund-quant-terminal/
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口，启动时创建索引
│   │   ├── config.py
│   │   ├── database.py      # MongoDB + 索引
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── schemas/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/                 # Vue 3 + Vite + Element Plus
├── docker-compose.yml       # MongoDB
└── README.md
```

---

## 六、环境变量

复制 `backend/.env.example` 为 `backend/.env`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| MONGODB_URL | MongoDB 连接 | mongodb://localhost:27017 |
| MONGODB_DB_NAME | 数据库名 | fund_quant |
| TUSHARE_TOKEN | Tushare Token（可选） | 空 |
| APP_DEBUG | 调试模式 | true |
| APP_HOST / APP_PORT | 服务地址 | 0.0.0.0:8000 |
| CORS_ORIGINS | 允许的前端源 | localhost:5173 |

---

## 七、API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/decisions/log` | 记录决策 |
| GET | `/api/decisions/list` | 决策列表 |
| GET | `/api/assets/summary` | 资产汇总 |
| POST | `/api/assets/update` | 更新资产 |
| POST | `/api/data/fetch` | 拉取数据 |
| GET | `/api/data/history` | 历史数据 |
| POST | `/api/analyze-portfolio` | 投资组合 AI 分析（Qwen/Grok） |
| GET | `/api/grok-prompt` | 获取 Grok 提示词（最新或指定版本） |
| POST | `/api/grok-prompt` | 保存新版本 |
| GET | `/api/grok-prompt/history` | 历史版本列表 |

---

## 八、功能特性

- **自动索引**：后端启动时为 `decision_logs`、`assets` 创建索引  
- **60 秒刷新**：前端每 60 秒刷新资产与决策数据  
- **一键 AI 分析**：资产配置页「一键 AI 分析」聚合持仓、新闻、市场指数，调用 LLM 生成投资建议，可应用到决策日志  
- **资产曲线**：绿/红区分盈利与亏损  
- **深色模式**：在设置中切换  

---

## 许可证

MIT
