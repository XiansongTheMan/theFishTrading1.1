# -*- coding: utf-8 -*-
"""修复 news 接口测试页中文乱码，保留 config 结构"""
import os

path = os.path.join(os.path.dirname(__file__), "src", "views", "WallstreetTestView.vue")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 按顺序替换，从长到短避免误伤
repl = [
    ('news???? - Card + Tabs', 'news接口测试 - Card + Tabs'),
    ('<!-- ?? Tab???? -->', '<!-- 一级 Tab：新闻源 -->'),
    ('<!-- ?? Tab????? -->', '<!-- 二级 Tab：接口类型 -->'),
    ('\n              ????\n            </ElLink>', '\n              查看原文\n            </ElLink>'),
    ('<!-- ?????? -->', '<!-- 关键字段卡片 -->'),
    ('<div class="field-label">来源链接</div>', '<div class="field-label">原文链接</div>'),
    ('title="查看完整响应"', 'title="请求与响应"'),
    ('/* ?????? tooltip */', '/* 情绪说明 tooltip */'),
    ('/* ========== ?? Tab?????ElTabs border-card? ========== */', '/* ========== 一级 Tab：新闻源（ElTabs border-card） ========== */'),
    ('/* ========== ?? Tab??????ElTabs card? ========== */', '/* ========== 二级 Tab：接口类型（ElTabs card） ========== */'),
    ('????????? - Card + news????', 'news接口测试 - Card + Tabs'),
    ('/** ? UTC ISO ???????? yyyy/mm/dd hh:mm:ss */', '/** 将 UTC ISO 时间转为北京时间 yyyy/mm/dd hh:mm:ss */'),
    ('text: "???? news API..."', 'text: "正在请求 news API..."'),
    ('ElMessage.warning("??????")', 'ElMessage.warning("请填写关键词")'),
    ('ElMessage.success("????")', 'ElMessage.success("请求成功")'),
    ('return ax.response?.data?.message ?? "????"', 'return ax.response?.data?.message ?? "请求失败"'),
    ('return "????"', 'return "未知错误"'),
    ('<h2 class="page-title">news????</h2>', '<h2 class="page-title">news接口测试</h2>'),
    ('label="???"', 'label="关键词"'),
    ('placeholder="?????"', 'placeholder="输入搜索词"'),
    ('label="??????"', 'label="保存至数据库"'),
    ('>????</ElButton>', '>执行测试</ElButton>'),
    ('<!-- ????lives ?? -->', '<!-- 时间线：lives 类型 -->'),
    ('<span>?????</span>', '<span>快讯时间线</span>'),
    ('? {{ parsedList.length }} ?', '共 {{ parsedList.length }} 条'),
    ('>????</ElLink>', '>查看原文</ElLink>'),
    ('<div><strong>???????</strong>??????</div>', '<div><strong>本地关键词计算</strong>，非接口返回</div>'),
    ('?????????????????????????????????', '正向词：利好、上涨、买入、大涨、看涨、反弹、增长、突破、增持、推荐'),
    ('?????????????????????????????????', '负向词：利空、下跌、卖出、大跌、看跌、回落、跌破、亏损、减持、预警'),
    ('?? = (???? - ????) / ?????? -1 ~ 1', '得分 = (正向次数 - 负向次数) / 总次数，范围 -1 ~ 1'),
    ('?? {{ item.sentiment }}', '情绪 {{ item.sentiment }}'),
    ('<!-- ???????? lives ?? parsed ? -->', '<!-- 关键字段卡片 -->'),
    ('<template #header>????</template>', '<template #header>关键字段</template>', 1),
    ('<div class="field-label">??</div>', '<div class="field-label">标题</div>', 1),
    ('<div class="field-label">????</div>', '<div class="field-label">发布时间</div>', 1),
    ('<div class="field-label">??</div>', '<div class="field-label">摘要</div>', 1),
    ('<div class="field-label">????</div>', '<div class="field-label">原文链接</div>', 1),
    ('>????</ElLink>', '>查看原文</ElLink>'),
    ('{{ item.summary || "?" }}', '{{ item.summary || "—" }}'),
    ('<span v-else>?</span>', '<span v-else>—</span>'),
    ('<!-- ?? JSON ???? -->', '<!-- 原始 JSON 折叠面板 -->'),
    ('<template #header>?? JSON</template>', '<template #header>原始 JSON</template>'),
    ('title="??????"', 'title="请求与响应"'),
    ('if (!isoStr) return "?"', 'if (!isoStr) return "—"'),
]

# 处理重复的 关键字段 - 第一个是 fields-card header，第二个可能在别处
for item in repl:
    if len(item) == 2:
        old, new = item
        c = c.replace(old, new, 1)
    else:
        old, new, cnt = item
        c = c.replace(old, new, cnt)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
