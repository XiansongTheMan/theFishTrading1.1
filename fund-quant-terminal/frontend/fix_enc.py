# -*- coding: utf-8 -*-
path = 'src/views/WallstreetTestView.vue'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
# Fix encoding only - keep config structure
r = [
    ('return "?"', 'return "\u2014"'),
    ('?? "????"', '?? "\u8bf7\u6c42\u5931\u8d25"'),
    ('"??????"', '"\u8bf7\u586b\u5199\u5173\u952e\u8bcd"'),
    ('"???? news API..."', '"\u6b63\u5728\u8bf7\u6c42 news API..."'),
    ('ElMessage.success("????")', 'ElMessage.success("\u8bf7\u6c42\u6210\u529f")'),
    ('/** ? UTC ISO ???????? yyyy/mm/dd hh:mm:ss */', '/** \u5c06 UTC ISO \u65f6\u95f4\u8f6c\u4e3a\u5317\u4eac\u65f6\u95f4 yyyy/mm/dd hh:mm:ss */'),
    ('????????? - Card + news????', '\u534e\u5c14\u8857\u89c1\u95fb\u63a5\u53e3\u6d4b\u8bd5 - Card + \u6df1\u8272\u6a21\u5f0f'),
    ('news????', 'news\u63a5\u53e3\u6d4b\u8bd5'),
    ('label="???"', 'label="\u5173\u952e\u8bcd"'),
    ('placeholder="?????"', 'placeholder="\u8f93\u5165\u641c\u7d22\u8bcd"'),
    ('label="??????"', 'label="\u4fdd\u5b58\u81f3\u6570\u636e\u5e93"'),
    ('>????</ElButton>', '>\u6267\u884c\u6d4b\u8bd5</ElButton>'),
    ('<span>?????</span>', '<span>\u5feb\u8baf\u65f6\u95f4\u7ebf</span>'),
    ('? {{ parsedList.length }} ?', '\u5171 {{ parsedList.length }} \u6761'),
    ('>????</ElLink>', '>\u67e5\u770b\u539f\u6587</ElLink>'),
    ('?? {{ item.sentiment }}', '\u60c5\u7eea {{ item.sentiment }}'),
    ('<template #header>????</template>', '<template #header>\u5173\u952e\u5b57\u6bb5</template>'),
    ('<div class="field-label">??</div>', '<div class="field-label">\u6807\u9898</div>'),
    ('<div class="field-label">????</div>', '<div class="field-label">\u53d1\u5e03\u65f6\u95f4</div>'),
    ('<div class="field-label">????</div>', '<div class="field-label">\u6765\u6e90\u94fe\u63a5</div>'),
    ('>????</ElLink>', '>\u6253\u5f00\u94fe\u63a5</ElLink>'),
    ('title="??????"', 'title="\u67e5\u770b\u5b8c\u6574\u54cd\u5e94"'),
    ('?? JSON', '\u539f\u59cb JSON'),
    ('if (!isoStr) return "?"', 'if (!isoStr) return "\u2014"'),
    ('return "????"', 'return "\u8bf7\u6c42\u5931\u8d25"'),
    ('<!-- ????lives ?? -->', '<!-- \u65f6\u95f4\u7ebf\uff1alives \u7c7b\u578b -->'),
    ('<div><strong>???????</strong>??????</div>', '<div><strong>\u672c\u5730\u5173\u952e\u8bcd\u8ba1\u7b97</strong>\uff0c\u975e\u63a5\u53e3\u8fd4\u56de</div>'),
    ('{{ item.summary || "?" }}', '{{ item.summary || "\u2014" }}'),
    ('<span v-else>?</span>', '<span v-else>\u2014</span>'),
    ('\u539f\u59cb JSON ????', '\u539f\u59cb JSON \u6298\u53e0\u9762\u677f'),
    ('<template #header>?? JSON</template>', '<template #header>\u539f\u59cb JSON</template>'),
    ('<div class="field-label">??</div>', '<div class="field-label">\u6458\u8981</div>'),
    ('<!-- ???????? lives ?? parsed ? -->', '<!-- \u5173\u952e\u5b57\u6bb5\u5361\u7247 -->'),
    ('/* ?????? tooltip */', '/* \u60c5\u7eea\u8ba1\u7b97\u8bf4\u660e tooltip */'),
]
for a, b in r:
    c = c.replace(a, b, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('ok')
