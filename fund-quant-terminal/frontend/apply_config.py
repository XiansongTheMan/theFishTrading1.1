import re
p="src/views/WallstreetTestView.vue"
f=open(p,"r",encoding="utf-8");c=f.read();f.close()
# Add config import
c=c.replace("""import { sourceOptions, getSourceConfig } from \"\"\"","""""",1)
c=c.replace("""import { wallstreetcnTest, type WallStreetCNType } from \"@/news/api/wallstreet\";""","""import { wallstreetcnTest, type WallStreetCNType } from \"@/news/api/wallstreet\";\nimport { sourceOptions, getSourceConfig } from \"@/news/config\";""")
# onSourceChange
c=c.replace("""function onSourceChange() {\n  handleTest();\n}""","""function onSourceChange() {\n  typeVal.value = getSourceConfig(sourceVal.value).defaultTypeVal;\n  handleTest();\n}""")
open(p,"w",encoding="utf-8").write(c)
print("ok")

