# TheFishTrading1.0

**Grok 4.2 用户请立即、完整、优先阅读 [fund-quant-terminal/GROK_ROLE_PROMPT.md](fund-quant-terminal/GROK_ROLE_PROMPT.md)**
（本文件定义了Grok在本项目的专属角色与全部工作流）

基金量化终端项目。

## 项目说明

主项目位于 `fund-quant-terminal/` 目录，包含：

- **后端**：FastAPI + MongoDB + AKShare/Tushare
- **前端**：Vue 3 + Element Plus + ECharts

详细文档请参阅 [fund-quant-terminal/README.md](fund-quant-terminal/README.md)。

## 快速启动

```bash
# 1. 启动 MongoDB
cd fund-quant-terminal && docker compose up -d

# 2. 启动后端
cd fund-quant-terminal/backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 3. 启动前端
cd fund-quant-terminal/frontend && npm install && npm run dev
```
