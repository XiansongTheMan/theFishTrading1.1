# -*- coding: utf-8 -*-
"""彻底重写 news 接口测试的一二级 Tab 样式"""
import os

path = os.path.join(os.path.dirname(__file__), "src", "views", "WallstreetTestView.vue")
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. 替换模板 - Tab 结构
old_tpl = """    <ElCard shadow="never" class="tab-card">
      <ElTabs v-model="sourceVal" type="border-card" @tab-change="onSourceChange" class="news-source-tabs">
        <ElTabPane v-for="src in sourceOptions" :key="src.value" :name="src.value" :label="src.label">
          <ElTabs v-model="typeVal" type="card" @tab-change="handleTest" class="news-type-tabs">
            <ElTabPane v-for="opt in typeOptions" :key="opt.value" :name="opt.value" :label="opt.label" />
          </ElTabs>
      <ElDivider class="form-divider" />
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
      </ElForm>
        </ElTabPane>
      </ElTabs>
    </ElCard>"""

new_tpl = """    <ElCard shadow="never" class="tab-card">
      <ElTabs v-model="sourceVal" type="border-card" class="tabs-level-1" @tab-change="onSourceChange">
        <ElTabPane v-for="src in sourceOptions" :key="src.value" :name="src.value" :label="src.label">
          <ElTabs v-model="typeVal" type="card" class="tabs-level-2" @tab-change="handleTest">
            <ElTabPane v-for="opt in typeOptions" :key="opt.value" :name="opt.value" :label="opt.label" />
          </ElTabs>
          <ElDivider class="form-divider" />
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
          </ElForm>
        </ElTabPane>
      </ElTabs>
    </ElCard>"""

c = c.replace(old_tpl, new_tpl)

# 2. 替换 style - 移除旧 tab 样式，写入新的
old_style = """<style scoped>
.wallstreet-test {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
}

.tab-card :deep(.el-card__body) {
  padding: 0;
}

.news-source-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 12px 16px 0;
  background: var(--el-fill-color-lighter);
}

.news-source-tabs :deep(.el-tabs__content) {
  padding: 16px;
}

.news-type-tabs :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.form-divider {
  margin: 16px 0;
}

.segment-wrapper {
  margin-bottom: 16px;
}

.segment-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.segment-row:last-of-type {
  margin-bottom: 0;
}

.segment-label {
  font-size: 0.9rem;
  color: var(--el-text-color-secondary);
  min-width: 64px;
}

.source-segmented {
  flex: 0 1 auto;
}

.type-segmented {
  flex: 1;
  min-width: 0;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
}

.form-row :deep(.el-form-item) {
  margin-bottom: 0;
}"""

new_style = """<style scoped>
.wallstreet-test {
  max-width: 900px;
}

.page-title {
  margin: 0 0 20px;
}

.tab-card :deep(.el-card__body) {
  padding: 0;
}

/* ========== 一级 Tab：新闻源（ElTabs border-card） ========== */
.tabs-level-1 :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.tabs-level-1 :deep(.el-tabs__nav-wrap) {
  padding: 0;
}
.tabs-level-1 :deep(.el-tabs__item) {
  font-size: 0.95rem;
  font-weight: 500;
  padding: 0 24px;
  height: 48px;
  line-height: 48px;
}
.tabs-level-1 :deep(.el-tabs__item.is-active) {
  color: var(--el-color-primary);
}
.tabs-level-1 :deep(.el-tabs__content) {
  padding: 20px;
}
.tabs-level-1 :deep(.el-tabs__active-bar) {
  height: 3px;
}

/* ========== 二级 Tab：接口类型（ElTabs card） ========== */
.tabs-level-2 :deep(.el-tabs__header) {
  margin: 0 0 16px;
  padding: 0;
  border: none;
  background: transparent;
}
.tabs-level-2 :deep(.el-tabs__nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  padding: 2px 0;
}
.tabs-level-2 :deep(.el-tabs__nav) {
  border: none;
}
.tabs-level-2 :deep(.el-tabs__item) {
  font-size: 0.875rem;
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
  border: 1px solid var(--el-border-color);
  border-right: none;
}
.tabs-level-2 :deep(.el-tabs__item:first-child) {
  border-radius: 4px 0 0 4px;
}
.tabs-level-2 :deep(.el-tabs__item:last-child) {
  border-right: 1px solid var(--el-border-color);
  border-radius: 0 4px 4px 0;
}
.tabs-level-2 :deep(.el-tabs__item.is-active) {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}
.tabs-level-2 :deep(.el-tabs__item.is-active + .el-tabs__item) {
  border-left-color: var(--el-color-primary);
}
.tabs-level-2 :deep(.el-tabs__content) {
  padding: 0;
}
.tabs-level-2 :deep(.el-tabs__active-bar) {
  display: none;
}
.tabs-level-2 :deep(.el-tabs__indicators) {
  display: none;
}

.form-divider {
  margin: 16px 0;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
}

.form-row :deep(.el-form-item) {
  margin-bottom: 0;
}"""

c = c.replace(old_style, new_style)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Done")
