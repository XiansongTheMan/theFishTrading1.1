# Fund Quant Terminal - 基金量化终端

生产级基金量化终端，支持 AKShare/Tushare 数据、决策日志、资产曲线。**默认使用 Qwen 大模型**，支持 Grok 等可选模型（通过 Token 配置切换）。

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
| POST `/api/wallstreetcn/test` | 华尔街见闻接口测试。**Body**: `{ type, code?, keyword?, limit?, channel?, cursor?, save_to_db? }`。`type` 可选: `lives`(实时快讯)、`articles`(文章)、`search`(个股搜索)、`quote`(行情快照，需 `code`)、`keyword`(关键词搜索，需 `keyword`)。返回原始 JSON 及解析字段(title、published_time、summary、url、sentiment)。供 AI 决策参考的股市情报来源。 |
| POST `/api/analyze-portfolio` | 一键 AI 分析。**Body**: `{ user_id?, model_type? }`。聚合资产汇总、近期新闻、市场快照、风险偏好，调用 Qwen/Grok 生成结构化投资建议（fund_code、action、amount、reason 等）。前端资产配置页「一键 AI 分析」调用此接口。 |

---

## 三、如何记录一次 AI 决策

### 步骤

1. 打开 **决策日志** 页面  
2. 点击 **新增决策**  
3. 填写表单：
   - **基金代码**：必填，如 `000001`
   - **用户动作**：买入 / 卖出 / 持有
   - **Grok 输入**：发送给 AI 的提示内容
   - **Grok 建议**：AI 的回复或建议
   - **交易金额**、**净值**、**手续费**、**盈亏**：按实际填写
   - **交易前/后资金**：可选，用于记录资金变动
   - **备注**：补充说明
4. 点击 **提交**  

买入/卖出提交后会自动调用 `/api/assets/update` 更新资本。

---

## 四、一键 AI 分析（投资组合分析）

在 **资产配置** 页面点击「一键 AI 分析」，系统将：

1. 聚合当前资产汇总、近期新闻（华尔街见闻）、市场快照（沪深300、基金指数）、用户风险偏好  
2. 调用 LLM（默认 Qwen，可配置 Grok）生成结构化投资建议  
3. 展示分析结果（基金代码、建议操作、金额、止盈止损、置信度、风险等级、分析理由）  
4. 支持「应用到决策日志」一键写入决策记录  

需在 **Token 配置** 中为对应 Agent（Qwen/Grok）添加 API Key。

---

## 五、决策记录与 AI 协作

### 工作流建议

1. 使用 **一键 AI 分析** 或 Agent 连接测试完成分析和决策  
2. 打开 **决策日志** 页面，点击 **新增决策**  
3. 从 AI 对话或分析结果中复制：
   - 输入问题 → 填入「Grok 输入」
   - 建议内容 → 填入「Grok 建议」
4. 填写基金代码、动作、金额等后提交  

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

## 六、项目结构

```
fund-quant-terminal/
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口，启动时创建索引
│   │   ├── config.py
│   │   ├── database.py      # MongoDB + 索引
│   │   ├── models/
│   │   ├── prompts/           # 系统提示词（如 fund_analyst_prompt.md）
│   │   ├── routers/
│   │   ├── services/          # PortfolioContextBuilder、PortfolioAnalyzer 等
│   │   └── schemas/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/                 # Vue 3 + Vite + Element Plus
├── docker-compose.yml       # MongoDB
└── README.md
```

---

## 七、环境变量

复制 `backend/.env.example` 为 `backend/.env`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| MONGODB_URL | MongoDB 连接 | mongodb://localhost:27017 |
| MONGODB_DB_NAME | 数据库名 | fund_quant |
| TUSHARE_TOKEN | Tushare Token（可选） | 空 |
| APP_DEBUG | 调试模式 | true |
| APP_HOST / APP_PORT | 服务地址 | 0.0.0.0:8000 |
| CORS_ORIGINS | 允许的前端源 | localhost:5173 |
| LLM_PROVIDER | 默认 LLM 提供商 | grok（可改为 qwen） |
| QWEN_API_KEY | 通义千问 API Key（Qwen） | 空 |
| GROK_API_KEY | Grok API Key | 空 |

---

## 八、API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/decisions/log` | 记录决策 |
| GET | `/api/decisions/list` | 决策列表 |
| GET | `/api/assets/summary` | 资产汇总 |
| POST | `/api/assets/update` | 更新资产 |
| POST | `/api/data/fetch` | 拉取数据 |
| GET | `/api/data/history` | 历史数据 |
| POST | `/api/wallstreetcn/test` | 华尔街见闻接口测试（快讯/文章/搜索/行情/关键词） |
| POST | `/api/analyze-portfolio` | 投资组合 AI 分析（聚合资产、新闻、市场，返回结构化建议） |
| GET | `/api/grok-prompt` | 获取 Grok 提示词（最新或指定版本） |
| POST | `/api/grok-prompt` | 保存新版本 |
| GET | `/api/grok-prompt/history` | 历史版本列表 |

---

## 九、功能特性

- **自动索引**：后端启动时为 `decision_logs`、`assets` 创建索引  
- **60 秒刷新**：前端每 60 秒刷新资产与决策数据  
- **一键 AI 分析**：资产配置页聚合持仓、新闻、市场指数，调用 Qwen/Grok 生成投资建议，可应用到决策日志  
- **资产曲线**：绿/红区分盈利与亏损  
- **深色模式**：在设置中切换  

---

## 十、Agent 角色设定与 /agent-prompts-test

Agent 角色设定支持 **Qwen**（默认）与 **Grok** 两种大模型，可通过统一聊天测试接口 `/api/agent-prompts-test` 进行连接与对话测试。

### 功能说明

- 在 **Agent 角色设定** 页面可切换 Qwen / Grok，配置角色模板与模型
- 使用 **连接测试** 或 **chat 测试** 验证 API Key 与模型是否可用
- **Token 配置** 中需先添加对应 Agent 的 API Key（Qwen 在 dashscope.console.aliyun.com 获取，Grok 在 console.x.ai 获取）

### 接口示例

**Grok 测试：**

```bash
curl -X POST "http://localhost:8000/api/agent-prompts-test" \
  -H "Content-Type: application/json" \
  -d '{"agent":"grok","content":"你好","messages":[]}'
```

**Qwen 测试：**

```bash
curl -X POST "http://localhost:8000/api/agent-prompts-test" \
  -H "Content-Type: application/json" \
  -d '{"agent":"qwen","content":"你好","messages":[]}'
```

### 响应格式

```json
{
  "code": 200,
  "data": {
    "ok": true,
    "content": "模型回复内容",
    "model": "grok-4-fast-reasoning",
    "provider": "grok",
    "error": null
  }
}
```

失败时 `ok` 为 `false`，`content` 与 `error` 为错误信息。

### 一键 AI 分析接口示例

```bash
curl -X POST "http://localhost:8000/api/analyze-portfolio" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"default","model_type":"qwen"}'
```

---

## 许可证

MIT
