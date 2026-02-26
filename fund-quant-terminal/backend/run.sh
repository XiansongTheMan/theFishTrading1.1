#!/bin/bash
# 后端启动脚本
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
