# -*- coding: utf-8 -*-
import re
p = r"d:\cursorProj\TheFishTrading1.0\fund-quant-terminal\frontend\src\views\AgentPrompt\AgentRoleSetting.vue"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()
c = re.sub(r'(templateName\.value \|\| promptContent\.value \|\| ")[^)]*\)\.trim\(\)\.slice\(0, 50\) \|\| "[^";]*', r'\1' + chr(0x672a)+chr(0x547d)+chr(0x540d) + '").trim().slice(0, 50) || "' + chr(0x672a)+chr(0x547d)+chr(0x540d) + '"', c)
c = re.sub(r'(ElMessage\.warning\("[\u4e00-\u9fff]+)[^"]*"\)', r'\1' + chr(0x5bb9) + '")', c)
c = re.sub(r'ElMessage\.success\("[^\"]*"\)', lambda m: 'ElMessage.success("' + (chr(0x5df2)+chr(0x4fdd)+chr(0x5b58) if chr(0x4fdd) in m.group(0) else chr(0x5df2)+chr(0x66f4)+chr(0x65b0) if chr(0x66f4) in m.group(0) else chr(0x5df2)+chr(0x5220)+chr(0x9664)) + '")', c)
c = re.sub(r'(templateName\.value \|\| ")[^"]*\)\.trim\(\) \|\| "[^";]*', r'\1' + chr(0x672a)+chr(0x547d)+chr(0x540d) + '").trim() || "' + chr(0x672a)+chr(0x547d)+chr(0x540d) + '"', c)
with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")