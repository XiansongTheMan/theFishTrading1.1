# -*- coding: utf-8 -*-
"""全局修复 news 接口测试及相关文件的中文编码问题"""
import os
import glob

FRONTEND = os.path.join(os.path.dirname(__file__), "src")

# WallstreetTestView.vue 专用替换表（旧文本 -> 新文本）
WALLSTREET_REPLACEMENTS = [
    ("????????? - Card + ????", "news接口测试 - Card + Tabs"),
    ("/** ? UTC ISO ???????? yyyy/mm/dd hh:mm:ss */", "/** 将 UTC ISO 时间转为北京时间 yyyy/mm/dd hh:mm:ss */"),
    ('if (!isoStr) return "?"', 'if (!isoStr) return "—"'),
    ('?? "????"', '?? "请求失败"'),
    ('return "????"', 'return "未知错误"'),
    ('ElMessage.warning("??????")', 'ElMessage.warning("请输入关键词")'),
    ('text: "???? news API..."', 'text: "正在请求 news API..."'),
    ('ElMessage.success("????")', 'ElMessage.success("请求成功")'),
    ('<h2 class="page-title">news????</h2>', '<h2 class="page-title">news接口测试</h2>'),
    ('<!-- ?? Tab???? -->', '<!-- 一级 Tab：新闻源 -->'),
    ('<!-- ?? Tab????? -->', '<!-- 二级 Tab：接口类型 -->'),
    ('label="???"', 'label="关键词"'),
    ('placeholder="?????"', 'placeholder="输入搜索词"'),
    ('label="??????"', 'label="保存至数据库"'),
    (">????</ElButton>", ">执行测试</ElButton>"),
    ("<!-- ????lives ?? -->", "<!-- 时间线：lives 类型 -->"),
    ("<span>?????</span>", "<span>快讯时间线</span>"),
    ("? {{ parsedList.length }} ?", "共 {{ parsedList.length }} 条"),
    (">????</ElLink>", ">查看原文</ElLink>"),
    ("<div><strong>???????</strong>??????</div>", "<div><strong>本地关键词计算</strong>，非接口返回</div>"),
    ("<div>?????????????????????????????????</div>", "<div>正向词：利好、上涨、买入、大涨、看涨、反弹、增长、突破、增持、推荐</div>"),
    ("<div>?????????????????????????????????</div><div>?? = (???? - ????) / ?????? -1 ~ 1</div>", "<div>负向词：利空、下跌、卖出、大跌、看跌、回落、跌破、亏损、减持、预警</div><div>得分 = (正向次数 - 负向次数) / 总次数，范围 -1 ~ 1</div>"),
    ("?? {{ item.sentiment }}", "情绪 {{ item.sentiment }}"),
    ("<!-- ?????? -->", "<!-- 关键字段卡片 -->"),
    ("<template #header>????</template>", "<template #header>关键字段</template>"),
    ('<div class="field-label">??</div>\n          <div class="field-value">{{ item.title }}</div>', '<div class="field-label">标题</div>\n          <div class="field-value">{{ item.title }}</div>'),
    ('<div class="field-label">????</div>\n          <div class="field-value">{{ formatBeijingTime', '<div class="field-label">发布时间</div>\n          <div class="field-value">{{ formatBeijingTime'),
    ('<div class="field-label">??</div>\n          <div class="field-value field-summary">', '<div class="field-label">摘要</div>\n          <div class="field-value field-summary">'),
    ('<div class="field-label">????</div>\n          <div class="field-value">\n            <ElLink', '<div class="field-label">原文链接</div>\n          <div class="field-value">\n            <ElLink'),
    ('{{ item.summary || "?" }}', '{{ item.summary || "—" }}'),
    ('<span v-else>?</span>', '<span v-else>—</span>'),
    ("<!-- ?? JSON ???? -->", "<!-- 原始 JSON 折叠面板 -->"),
    ("<template #header>?? JSON</template>", "<template #header>原始 JSON</template>"),
    ('title="??????"', 'title="请求与响应"'),
    ("/* ?????? tooltip */", "/* 情绪说明 tooltip */"),
]

# 修复 getErrorMessage 中的 ??
def fix_get_error_message(content):
    # return ax.response?.data?.message ?? "????" 和 return "????"
    import re
    content = re.sub(r'return ax\.response\?\.data\?\.message \?\? "?\?"+', 'return ax.response?.data?.message ?? "请求失败"', content)
    content = content.replace('return "????"', 'return "未知错误"')
    return content


def fix_wallstreet(path):
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    orig = c
    for old, new in WALLSTREET_REPLACEMENTS:
        c = c.replace(old, new)

    # 处理 sentiment tooltip 的两行（顺序相关）
    c = c.replace(
        """<div>?????????????????????????????????</div>
                  <div>?????????????????????????????????</div><div>?? = (???? - ????) / ?????? -1 ~ 1</div>""",
        """<div>正向词：利好、上涨、买入、大涨、看涨、反弹、增长、突破、增持、推荐</div>
                  <div>负向词：利空、下跌、卖出、大跌、看跌、回落、跌破、亏损、减持、预警</div><div>得分 = (正向次数 - 负向次数) / 总次数，范围 -1 ~ 1</div>""",
    )

    c = fix_get_error_message(c)

    if c != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        return True
    return False


def main():
    vue_path = os.path.join(FRONTEND, "views", "WallstreetTestView.vue")
    if os.path.exists(vue_path):
        if fix_wallstreet(vue_path):
            print("Fixed: WallstreetTestView.vue")
        else:
            print("No changes: WallstreetTestView.vue (may already be fixed or pattern mismatch)")
    else:
        print("Not found:", vue_path)

    # 扫描 src 下其他可能乱码的文件
    for ext in ["*.vue", "*.ts", "*.js"]:
        for p in glob.glob(os.path.join(FRONTEND, "**", ext), recursive=True):
            if "WallstreetTestView" in p or "node_modules" in p:
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
                if "??" in text and "?? " not in text and "??." not in text:
                    # 可能是误报（?? 是合法 JS 操作符），仅检查明显乱码
                    if "?" * 4 in text or "????" in text:
                        print("Check:", p)
            except Exception as e:
                print("Skip", p, e)

    print("Done")


if __name__ == "__main__":
    main()
