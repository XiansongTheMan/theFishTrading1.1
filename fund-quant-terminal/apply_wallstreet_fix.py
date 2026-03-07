# -*- coding: utf-8 -*-
import os
path = os.path.join(os.path.dirname(__file__), "frontend", "src", "views", "WallstreetTestView.vue")
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''const typeOptions: { value: WallStreetCNType; label: string }[] = [
  { value: "lives", label: "实时快讯" },
  { value: "articles", label: "文章" },
  { value: "search", label: "个股搜索" },
  { value: "quote", label: "行情快照" },
  { value: "keyword", label: "关键词搜索" },
];

const typeVal = ref<WallStreetCNType>("lives");
const codeVal = ref("");
const keywordVal = ref("");'''

new = '''interface TypeOption {
  value: string;
  label: string;
  type: WallStreetCNType;
  channel?: string;
}

const typeOptions: TypeOption[] = [
  { value: "lives:global-channel", label: "实时快讯", type: "lives", channel: "global-channel" },
  { value: "lives:a-stock-channel", label: "A股", type: "lives", channel: "a-stock-channel" },
  { value: "lives:goldc-channel", label: "黄金", type: "lives", channel: "goldc-channel" },
  { value: "lives:us-stock-channel", label: "美股", type: "lives", channel: "us-stock-channel" },
  { value: "lives:tech-channel", label: "科技", type: "lives", channel: "tech-channel" },
  { value: "lives:forex-channel", label: "金融", type: "lives", channel: "forex-channel" },
  { value: "lives:oil-channel", label: "石油", type: "lives", channel: "oil-channel" },
  { value: "lives:bond-channel", label: "债券", type: "lives", channel: "bond-channel" },
  { value: "lives:forex-fx", label: "外汇", type: "lives", channel: "forex-channel" },
  { value: "lives:commodity-channel", label: "大宗", type: "lives", channel: "commodity-channel" },
  { value: "lives:hk-stock-channel", label: "港股", type: "lives", channel: "hk-stock-channel" },
  { value: "keyword", label: "关键词搜索", type: "keyword" },
];

const typeVal = ref("lives:global-channel");
const keywordVal = ref("");'''

if old not in content:
    # try corrupted version
    old = '''const typeOptions: { value: WallStreetCNType; label: string }[] = [
  { value: "lives", label: "????" },
  { value: "articles", label: "??" },
  { value: "search", label: "????" },
  { value: "quote", label: "????" },
  { value: "keyword", label: "?????" },
];

const typeVal = ref<WallStreetCNType>("lives");
const codeVal = ref("");
const keywordVal = ref("");'''
    if old not in content:
        print("OLD BLOCK NOT FOUND")
        exit(1)

content = content.replace(old, new)

# fix needCode, needKeyword
content = content.replace(
    'const needCode = computed(() => typeVal.value === "quote");',
    "const currentOpt = computed(() => typeOptions.find((t) => t.value === typeVal.value) ?? typeOptions[0]);"
)
content = content.replace(
    'const needKeyword = computed(() => typeVal.value === "search" || typeVal.value === "keyword");',
    'const needKeyword = computed(() => currentOpt.value.type === "keyword");'
)

# fix showTimeline
content = content.replace(
    "() => parsedList.value.length > 0 && (typeVal.value === \"lives\" || typeVal.value === \"articles\")",
    "() => parsedList.value.length > 0 && currentOpt.value.type === \"lives\""
)

# fix handleTest - remove codeVal, add channel
content = content.replace(
    """  if (needCode.value && !codeVal.value.trim()) {
    ElMessage.warning("行情快照需填写股票代码");
    return;
  }
  if (needKeyword.value""",
    """  if (needKeyword.value"""
)

content = content.replace(
    """    const res = (await wallstreetcnTest({
      type: typeVal.value,
      code: codeVal.value.trim() || undefined,
      keyword: keywordVal.value.trim() || undefined,
      limit: limitVal.value,
      save_to_db: saveToDb.value,
    }))""",
    """    const opt = currentOpt.value;
    const res = (await wallstreetcnTest({
      type: opt.type,
      channel: opt.channel,
      keyword: keywordVal.value.trim() || undefined,
      limit: limitVal.value,
      save_to_db: saveToDb.value,
    }))"""
)

# Replace ElSelect with ElTabs in template
old_form = '''      <ElForm label-position="top" class="form-row">
        <ElFormItem label="接口类型">
          <ElSelect v-model="typeVal" placeholder="选择类型" style="width: 160px">
            <ElOption v-for="opt in typeOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="needCode" label="股票代码">
          <ElInput v-model="codeVal" placeholder="如 600519" style="width: 140px" clearable />
        </ElFormItem>
        <ElFormItem v-if="needKeyword" label="关键词">
          <ElInput v-model="keywordVal" placeholder="输入搜索词" style="width: 180px" clearable />
        </ElFormItem>
        <ElFormItem label="Limit">
          <ElInputNumber v-model="limitVal" :min="1" :max="100" style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="保存至数据库">
          <ElSwitch v-model="saveToDb" />
        </ElFormItem>
        <ElFormItem label=" ">
          <ElButton type="primary" :loading="loading" @click="handleTest">执行测试</ElButton>
        </ElFormItem>
      </ElForm>'''

new_form = '''      <ElTabs v-model="typeVal" type="card" @tab-change="handleTest" class="type-tabs">
        <ElTabPane
          v-for="opt in typeOptions"
          :key="opt.value"
          :name="opt.value"
          :label="opt.label"
        />
      </ElTabs>
      <ElForm label-position="top" class="form-row">
        <ElFormItem v-if="needKeyword" label="关键词">
          <ElInput v-model="keywordVal" placeholder="输入搜索词" style="width: 180px" clearable />
        </ElFormItem>
        <ElFormItem label="Limit">
          <ElInputNumber v-model="limitVal" :min="1" :max="100" style="width: 120px" />
        </ElFormItem>
        <ElFormItem label="保存至数据库">
          <ElSwitch v-model="saveToDb" />
        </ElFormItem>
        <ElFormItem label=" ">
          <ElButton type="primary" :loading="loading" @click="handleTest">执行测试</ElButton>
        </ElFormItem>
      </ElForm>'''

# Handle possible encoding issues in template
for o, n in [
    ('<ElFormItem label="接口类型">', '<ElFormItem v-if="needKeyword" label="关键词">'),
    ('<ElSelect v-model="typeVal"', '<ElInput v-model="keywordVal"'),
]:
    pass  # skip

content = content.replace(old_form, new_form)

# Add ElTabs, ElTabPane to imports
content = content.replace(
    "ElSelect,\n  ElOption,",
    "ElTabs,\n  ElTabPane,"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
