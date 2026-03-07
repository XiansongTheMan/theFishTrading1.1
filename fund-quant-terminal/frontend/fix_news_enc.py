# -*- coding: utf-8 -*-
path = "src/views/WallstreetTestView.vue"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
r = [
    ("????????? - Card + news????", "华尔街见闻接口测试 - Card + 深色模式"),
    ("/** ? UTC ISO ???????? yyyy/mm/dd hh:mm:ss */", "/** 将 UTC ISO 时间转为北京时间 yyyy/mm/dd hh:mm:ss */"),
    ('text: "???? news API..."', 'text: "正在请求 news API..."'),
    ('ElMessage.warning("??????")', 'ElMessage.warning("请填写关键词")'),
    ('ElMessage.success("????")', 'ElMessage.success("请求成功")'),
    ('return ax.response?.data?.message ?? "????"', 'return ax.response?.data?.message ?? "请求失败"'),
    ('return "????"', 'return "请求失败"'),
    ("<h2 class=`"page-title`">news????</h2>", "<h2 class=`"page-title`">news接口测试</h2>"),
    ('label="???"', 'label="关键词"'),
    ('placeholder="?????"', 'placeholder="输入搜索词"'),
    ('label="??????"', 'label="保存至数据库"'),
    (">????</ElButton>", ">执行测试</ElButton>"),
    ("<!-- ????lives ?? -->", "<!-- 时间线：lives 类型 -->"),
    ("<span>?????</span>", "<span>快讯时间线</span>"),
    ("? {{ parsedList.length }} ?", "共 {{ parsedList.length }} 条"),
    (">????</ElLink>", ">查看原文</ElLink>"),
    ("<div><strong>???????</strong>??????</div>", "<div><strong>本地关键词计算</strong>，非接口返回</div>"),
    ("?? {{ item.sentiment }}", "情绪 {{ item.sentiment }}"),
    ("<!-- ???????? lives ?? parsed ? -->", "<!-- 关键字段卡片 -->"),
    ("<template #header>????</template>", "<template #header>关键字段</template>"),
    ("<div class=`"field-label`">??</div>", "<div class=`"field-label`">标题</div>"),
    ("<!-- ?? JSON ???? -->", "<!-- 原始 JSON 折叠面板 -->"),
    ("<template #header>?? JSON</template>", "<template #header>原始 JSON</template>"),
    ('title="??????"', 'title="查看完整响应"'),
    ('if (!isoStr) return "?"', 'if (!isoStr) return "—"'),
]
for a, b in r:
    c = c.replace(a, b, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("ok")