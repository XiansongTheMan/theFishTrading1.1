Grok 4.2 用户请立即、完整、优先阅读 GROK_ROLE_PROMPT.md
（本文件定义了Grok在本项目的专属角色与全部工作流）

# Fund Quant Terminal - 基金量化终端

生产级基金量化终端，支持 AKShare/Tushare 数据、决策日志、资产曲线，为未来与 Grok 4.2 衔接预留接口。

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

---

## 三、如何记录一次 Grok 决策

### 步骤

1. 打开 **决策日志** 页面  
2. 点击 **新增决策**  
3. 填写表单：
   - **基金代码**：必填，如 `000001`
   - **用户动作**：买入 / 卖出 / 持有
   - **Grok 输入**：发送给 Grok 的提示内容
   - **Grok 建议**：Grok 的回复或建议
   - **交易金额**、**净值**、**手续费**、**盈亏**：按实际填写
   - **交易前/后资金**：可选，用于记录资金变动
   - **备注**：补充说明
4. 点击 **提交**  

买入/卖出提交后会自动调用 `/api/assets/update` 更新资本。

---

## 四、与 Grok 4.2 衔接方式（Grok 协作指南）

> **重要**：请优先阅读 [GROK_ROLE_PROMPT.md](GROK_ROLE_PROMPT.md)，该文件定义了 Grok 的强制系统角色提示词。

### 工作流建议

1. 在 Grok 4.2 中完成分析和决策  
2. 打开 **决策日志** 页面，点击 **新增决策**  
3. 从 Grok 对话中复制：
   - 输入问题 → 填入「Grok 输入」
   - 建议内容 → 填入「Grok 建议」
4. 填写基金代码、动作、金额等后提交  

### 未来扩展

- **复制最新记录给我（Grok 4.2）**：打开决策日志页面，找到最新一条记录，将「Grok 输入」和「Grok 建议」复制给 Grok 作为上下文，或复制整条 JSON 数据
- **API 对接**：后续可增加 Grok API 调用，将决策表单自动写入并同步到 Grok  

### 数据格式示例

```json
{
  "grok_prompt": "分析 000001 华夏成长混合当前是否适合买入",
  "grok_response": "综合净值走势与估值，建议观望或小仓位定投...",
  "user_action": "hold",
  "fund_code": "000001",
  "amount_rmb": 0,
  "notes": "Grok 建议观望"
}
```

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
| GET | `/api/grok-prompt` | 获取 Grok 提示词（最新或指定版本） |
| POST | `/api/grok-prompt` | 保存新版本 |
| GET | `/api/grok-prompt/history` | 历史版本列表 |

---

## 八、功能特性

- **自动索引**：后端启动时为 `decision_logs`、`assets` 创建索引  
- **60 秒刷新**：前端每 60 秒刷新资产与决策数据  
- **资产曲线**：绿/红区分盈利与亏损  
- **深色模式**：在设置中切换  

---

## 许可证

MIT
