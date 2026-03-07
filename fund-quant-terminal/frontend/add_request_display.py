# -*- coding: utf-8 -*-
import os
path = os.path.join(os.path.dirname(__file__), "src", "views", "WallstreetTestView.vue")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old1 = """  try {
    const opt = currentOpt.value;
    const res = (await wallstreetcnTest({
      type: opt.type,
      channel: opt.channel,
      keyword: keywordVal.value.trim() || undefined,
      limit: limitVal.value,
      save_to_db: saveToDb.value,
    })) as { data?: Record<string, unknown> };
    result.value = res?.data ?? null;"""

new1 = """  try {
    const opt = currentOpt.value;
    const req = {
      type: opt.type,
      channel: opt.channel,
      keyword: keywordVal.value.trim() || undefined,
      limit: limitVal.value,
      save_to_db: saveToDb.value,
    };
    lastRequest.value = { ...req };
    const res = (await wallstreetcnTest(req)) as { data?: Record<string, unknown> };
    result.value = res?.data ?? null;"""

old2 = """<template #header>?? JSON</template>
      <ElCollapse>
        <ElCollapseItem title="??????" name="raw">"""

new2 = """<template #header>请求与响应</template>
      <ElCollapse>
        <ElCollapseItem title="发送的请求" name="req">
          <pre class="json-pre"><code>{{ requestJson }}</code></pre>
        </ElCollapseItem>
        <ElCollapseItem title="完整响应" name="raw">"""

if old1 in c:
    c = c.replace(old1, new1)
    print("1 ok")
else:
    print("1 not found")

# old2 might have ?? from encoding - try matching
import re
pat = r'<template #header>.*?</template>\s*<ElCollapse>\s*<ElCollapseItem title=".*?" name="raw">'
if re.search(pat, c, re.DOTALL):
    c = re.sub(
        pat,
        '<template #header>请求与响应</template>\n      <ElCollapse>\n        <ElCollapseItem title="发送的请求" name="req">\n          <pre class="json-pre"><code>{{ requestJson }}</code></pre>\n        </ElCollapseItem>\n        <ElCollapseItem title="完整响应" name="raw">',
        c,
        count=1
    )
    print("2 ok (regex)")
elif "ElCollapseItem" in c and "name=\"raw\"" in c:
    # Fallback: replace just the collapse structure
    old_collapse = """<ElCollapse>
        <ElCollapseItem title="??????" name="raw">
          <pre class="json-pre"><code>{{ rawJson }}</code></pre>
        </ElCollapseItem>
      </ElCollapse>"""
    new_collapse = """<ElCollapse>
        <ElCollapseItem title="发送的请求" name="req">
          <pre class="json-pre"><code>{{ requestJson }}</code></pre>
        </ElCollapseItem>
        <ElCollapseItem title="完整响应" name="raw">
          <pre class="json-pre"><code>{{ rawJson }}</code></pre>
        </ElCollapseItem>
      </ElCollapse>"""
    if old_collapse in c:
        c = c.replace(old_collapse, new_collapse)
        print("2 ok (fallback)")
    else:
        # Match with ?? chars
        import re
        c = re.sub(
            r'<ElCollapse>\s*<ElCollapseItem title="[^"]*" name="raw">\s*<pre class="json-pre"><code>\{\{ rawJson \}\}</code></pre>\s*</ElCollapseItem>\s*</ElCollapse>',
            '''<ElCollapse>
        <ElCollapseItem title="发送的请求" name="req">
          <pre class="json-pre"><code>{{ requestJson }}</code></pre>
        </ElCollapseItem>
        <ElCollapseItem title="完整响应" name="raw">
          <pre class="json-pre"><code>{{ rawJson }}</code></pre>
        </ElCollapseItem>
      </ElCollapse>''',
            c,
            count=1
        )
        print("2 ok (regex2)")

# Also update header
c = re.sub(r'<template #header>[^<]+</template>', '<template #header>请求与响应</template>', c, count=1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
