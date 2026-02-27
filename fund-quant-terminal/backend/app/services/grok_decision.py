# =====================================================
# Grok 决策提示词生成
# 基于新闻 + 简单情绪分析，生成量化基金经理风格的决策提示
# =====================================================

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.data_fetcher import DataFetcherService
from app.utils.logger import logger

NEWS_COLLECTION = "news_raw"
HOURS_WINDOW = 72

# 简单情绪关键词（可扩展）
POSITIVE_KEYWORDS = [
    "利好", "大涨", "上涨", "看涨", "乐观", "bullish", "rally", "增长", "突破",
    "创新高", "反弹", "回暖", "向好", "超预期", "盈利", "增持", "推荐",
]
NEGATIVE_KEYWORDS = [
    "利空", "大跌", "下跌", "看跌", "悲观", "bearish", "回落", "跌破",
    "亏损", "减持", "预警", "风险", "下滑", "承压", "谨慎", "抛售",
]


def _count_sentiment(text: str) -> Tuple[int, int]:
    """统计文本中正负向关键词出现次数"""
    if not text or not isinstance(text, str):
        return 0, 0
    t = text.lower().strip()
    pos = sum(1 for k in POSITIVE_KEYWORDS if k.lower() in t)
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k.lower() in t)
    return pos, neg


async def generate_grok_prompt(
    fund_code: str,
    db: AsyncIOMotorDatabase,
    limit: int = 10,
    include_news_list: bool = True,
    custom_news_links: Optional[List[str]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    生成 Grok 决策提示词
    - custom_news_links: 若提供，则按 link 查询指定新闻；否则按 fund_code + 72h 查询
    - 简单情绪分析：统计正/负向关键词
    Returns: (prompt, news_summary_list)
    """
    code = (fund_code or "").strip().split(".")[0] if fund_code else ""
    code = code.zfill(6) if code else ""

    # 1. 获取基金名称
    display_name = "市场"
    if code:
        data_service = DataFetcherService()
        fund_name: Optional[str] = None
        try:
            fund_name = await data_service.get_fund_name(code)
        except Exception as e:
            logger.debug("get_fund_name 失败 %s: %s", code, e)
        display_name = fund_name or f"基金{code}"

    # 2. 获取新闻：指定 link 列表 或 按 fund+时间 查询
    if custom_news_links and len(custom_news_links) > 0:
        links = [l.strip() for l in custom_news_links if l and l.strip()]
        docs = await db[NEWS_COLLECTION].find({"link": {"$in": links}}).sort("pub_date", -1).limit(limit).to_list(length=limit)
    else:
        cutoff = datetime.utcnow() - timedelta(hours=HOURS_WINDOW)
        q: Dict[str, Any] = {"pub_date": {"$gte": cutoff}}
        if code:
            q["$or"] = [
                {"fund_code": code},
                {"fund_code": {"$in": [None, ""]}},
                {"fund_code": {"$exists": False}},
            ]
        else:
            q["$or"] = [
                {"fund_code": {"$in": [None, ""]}},
                {"fund_code": {"$exists": False}},
            ]
        cursor = db[NEWS_COLLECTION].find(q).sort("pub_date", -1).limit(limit)
        docs = await cursor.to_list(length=limit)

    # 3. 构建新闻列表 + 简单情绪统计 + news_summary
    total_pos, total_neg = 0, 0
    lines: List[str] = []
    news_summary: List[Dict[str, Any]] = []
    for i, d in enumerate(docs, 1):
        title = (d.get("title") or "").strip() or "(无标题)"
        summary = (d.get("content_summary") or "").strip()[:200]
        link = (d.get("link") or "").strip()
        pub = d.get("pub_date")
        pub_str = pub.isoformat()[:19] if pub and hasattr(pub, "isoformat") else str(pub or "")
        source = d.get("source") or ""

        text_for_sentiment = f"{title} {summary}"
        pos, neg = _count_sentiment(text_for_sentiment)
        total_pos += pos
        total_neg += neg

        if include_news_list:
            news_summary.append({
                "title": title,
                "link": link,
                "pub_date": pub_str,
                "source": source,
                "content_summary": summary[:300] if summary else "",
            })

        line = f"{i}. [{pub_str}] {title}"
        if summary:
            line += f"\n   摘要: {summary[:150]}..."
        if link:
            line += f"\n   链接: {link}"
        if source:
            line += f" (来源: {source})"
        lines.append(line)

    news_block = "\n".join(lines) if lines else "（暂无近期新闻）"

    # 4. 情绪汇总
    sentiment_note = ""
    if total_pos > 0 or total_neg > 0:
        sentiment_note = f"\n简单情绪统计：正向关键词 {total_pos} 次，负向关键词 {total_neg} 次。"
    else:
        sentiment_note = "\n（未检测到明显情绪关键词）"

    # 5. 输出结构化提示
    scope = f"{display_name}（代码 {code}）" if code else "市场"
    prompt = f"""以下是{scope}相关新闻与市场情绪汇总：

【新闻列表】
{news_block}
{sentiment_note}

请以专业量化基金经理身份，基于以上信息，给出：
1. 建议：买入 / 卖出 / 维持
2. 详细理由（结合新闻与情绪简要分析）
3. 建议仓位（如 0%-100% 或具体比例）
4. 止损位（如适用）"""
    return prompt, news_summary
