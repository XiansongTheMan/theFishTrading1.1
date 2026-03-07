# -*- coding: utf-8 -*-
"""修复 news 接口测试页的中文乱码（问号）"""
import re
import os

path = os.path.join(os.path.dirname(__file__), "src", "views", "WallstreetTestView.vue")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 按顺序替换，避免误伤
repl = [
    (r'label: "????"', 'label: "实时快讯"'),
    (r'label: "A\?"', 'label: "A股"'),
    (r'label: "??", type: "lives", channel: "goldc-channel"', 'label: "黄金", type: "lives", channel: "goldc-channel"'),
    (r'label: "??", type: "lives", channel: "us-stock-channel"', 'label: "美股", type: "lives", channel: "us-stock-channel"'),
    (r'label: "??", type: "lives", channel: "tech-channel"', 'label: "科技", type: "lives", channel: "tech-channel"'),
    (r'label: "??", type: "lives", channel: "bond-channel"', 'label: "金融", type: "lives", channel: "bond-channel"'),
    (r'value: "lives:finance-bonds", label: "??"', 'value: "lives:finance-bonds", label: "金融"'),
    (r'label: "??", type: "lives", channel: "oil-channel"', 'label: "石油", type: "lives", channel: "oil-channel"'),
    (r'value: "lives:bond-channel", label: "??"', 'value: "lives:bond-channel", label: "债券"'),
    (r'label: "??", type: "lives", channel: "forex-channel"', 'label: "外汇", type: "lives", channel: "forex-channel"'),
    (r'value: "lives:forex-fx", label: "??"', 'value: "lives:forex-fx", label: "外汇"'),
    (r'label: "??", type: "lives", channel: "commodity-channel"', 'label: "大宗", type: "lives", channel: "commodity-channel"'),
    (r'label: "??", type: "lives", channel: "hk-stock-channel"', 'label: "港股", type: "lives", channel: "hk-stock-channel"'),
    (r'label: "?????"', 'label: "关键词搜索"'),
    (r'return "????"', 'return "请求失败"'),
    (r'ElMessage.warning\("??????"\)', 'ElMessage.warning("请填写关键词")'),
    (r'text: "????????? API..."', 'text: "正在请求 news API..."'),
    (r'ElMessage.success\("????"\)', 'ElMessage.success("请求成功")'),
    (r'<h2 class="page-title">.*?</h2>', '<h2 class="page-title">news接口测试</h2>'),
    (r'label="???"', 'label="关键词"'),
    (r'placeholder="?????"', 'placeholder="输入搜索词"'),
    (r'label="??????"', 'label="保存至数据库"'),
    (r'>????</ElButton>', '>执行测试</ElButton>'),
    (r'<span>?????</span>', '<span>快讯时间线</span>'),
    (r'\? \{\{ parsedList.length \}\} \?', '共 {{ parsedList.length }} 条'),
    (r'>????</ElLink>', '>查看原文</ElLink>'),
    (r'?? \{\{ item.sentiment \}\}', '情绪 {{ item.sentiment }}'),
    (r'<template #header>????</template>', '<template #header>关键字段</template>'),
    (r'<div class="field-label">??</div>', '<div class="field-label">标题</div>', 1),
    (r'<div class="field-label">????</div>', '<div class="field-label">发布时间</div>'),
    (r'<div class="field-label">????</div>', '<div class="field-label">来源链接</div>'),
    (r'>????</ElLink>', '>打开链接</ElLink>'),
    (r'title="查看完整响应"', 'title="完整响应"'),
]

# 简单替换
for old, new in repl:
    if "??" in old or "?" in old:
        c = c.replace(old, new, 1) if isinstance(old, str) else re.sub(old, new, c, count=1)
    else:
        c = re.sub(old, new, c, count=1) if ".*?" in old else c.replace(old, new, 1)

# 修复 formatBeijingTime 中的 em dash
c = re.sub(r'if \(!isoStr\) return "\?"', 'if (!isoStr) return "—"', c)

# 修复注释
c = c.replace("/** ? UTC ISO ???????? yyyy/mm/dd hh:mm:ss */", "/** 将 UTC ISO 时间转为北京时间 yyyy/mm/dd hh:mm:ss */")

# 修复 tooltip 中的中文
c = re.sub(r'<div><strong>???????</strong>??????</div>', '<div><strong>本地关键词计算</strong>，非接口返回</div>', c)
c = re.sub(r'<div>?????????????????????????????????</div>', '<div>正向词：利好、上涨、买入、大涨、看涨、反弹、增长、突破、增持、推荐</div>', c, count=1)
c = re.sub(r'<div>?????????????????????????????????</div>', '<div>负向词：利空、下跌、卖出、大跌、看跌、回落、跌破、亏损、减持、预警</div>', c, count=1)
c = re.sub(r'<div>?? = \(???? - ????\) / ?????? -1 ~ 1</div>', '<div>得分 = (正向次数 - 负向次数) / 总次数，范围 -1 ~ 1</div>', c)

# 修复摘要中的 —
c = re.sub(r'\{\{ item\.summary \|\| "\?" \}\}', '{{ item.summary || "—" }}', c)
c = re.sub(r'<span v-else>\?</span>', '<span v-else>—</span>', c)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done: 已修复中文编码")
