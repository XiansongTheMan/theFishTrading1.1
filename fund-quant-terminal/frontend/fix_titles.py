# -*- coding: utf-8 -*-
import re
path = "src/views/WallstreetTestView.vue"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = re.sub(r'title="[^"]*" name="req"', 'title="发送的请求" name="req"', c)
c = re.sub(r'title="[^"]*" name="raw"', 'title="完整响应" name="raw"', c)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("ok")
