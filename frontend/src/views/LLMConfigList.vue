<template>
  <div class="llm-config-list">
    <div class="header">
      <h1>LLM 模型配置</h1>
      <el-button type="primary" @click="showAddDialog = true">添加配置</el-button>
    </div>

    <el-table :data="configs" stripe>
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="provider_type" label="类型" width="160">
        <template #default="{ row }">
          <el-tag :type="providerTagType(row.provider_type)" size="small">
            {{ providerLabel(row.provider_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="模型" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="m in row.available_models" :key="m" size="small" style="margin: 2px">{{ m }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="api_key" label="API Key" width="160" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="editConfig(row)">编辑</el-button>
          <el-button size="small" type="success" @click="testConfig(row.id)" :loading="testingId === row.id">测试</el-button>
          <el-button size="small" type="danger" @click="deleteConfig(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" :title="editingConfig ? '编辑配置' : '添加配置'" width="650px">
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="配置名称">
          <el-input v-model="configForm.name" placeholder="如：OpenAI GPT-4o" />
        </el-form-item>
        <el-form-item label="Provider 类型">
          <el-select v-model="configForm.provider_type" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="OpenAI 兼容 (Gemini/DeepSeek/Ollama 等)" value="openai_compatible" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="configForm.api_key" type="password" show-password :placeholder="editingConfig ? '留空保持不变' : '输入 API Key'" />
        </el-form-item>
        <el-form-item v-if="configForm.provider_type === 'openai_compatible'" label="Base URL">
          <el-input v-model="configForm.base_url" placeholder="如：https://generativelanguage.googleapis.com/v1beta/openai/" />
        </el-form-item>
        <el-form-item label="可用模型">
          <div style="width: 100%">
            <div v-for="(model, idx) in configForm.available_models" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px">
              <el-input v-model="configForm.available_models[idx]" placeholder="模型名称" />
              <el-button type="danger" size="small" @click="configForm.available_models.splice(idx, 1)">删除</el-button>
            </div>
            <el-button size="small" @click="configForm.available_models.push('')">添加模型</el-button>
          </div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="configForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmConfigApi, type LLMConfig } from '@/api/llmConfigs'

const configs = ref<LLMConfig[]>([])
const showAddDialog = ref(false)
const saving = ref(false)
const testingId = ref('')
const editingConfig = ref<LLMConfig | null>(null)

const defaultForm = {
  name: '',
  provider_type: 'openai',
  api_key: '',
  base_url: '',
  available_models: [''] as string[],
  is_active: true,
}

const configForm = reactive({ ...defaultForm })

const providerLabel = (type: string) => {
  const map: Record<string, string> = { openai: 'OpenAI', anthropic: 'Anthropic', openai_compatible: 'OpenAI 兼容' }
  return map[type] || type
}

const providerTagType = (type: string) => {
  const map: Record<string, string> = { openai: 'success', anthropic: 'warning', openai_compatible: 'primary' }
  return map[type] || 'info'
}

const editConfig = (config: LLMConfig) => {
  editingConfig.value = config
  Object.assign(configForm, {
    name: config.name,
    provider_type: config.provider_type,
    api_key: config.api_key,
    base_url: config.base_url,
    available_models: [...config.available_models],
    is_active: config.is_active,
  })
  showAddDialog.value = true
}

const saveConfig = async () => {
  saving.value = true
  try {
    const data = {
      ...configForm,
      available_models: configForm.available_models.filter(m => m.trim()),
    }
    if (editingConfig.value) {
      await llmConfigApi.update(editingConfig.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await llmConfigApi.create(data as any)
      ElMessage.success('添加成功')
    }
    showAddDialog.value = false
    editingConfig.value = null
    Object.assign(configForm, defaultForm)
    configs.value = (await llmConfigApi.list() as any) || []
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const testConfig = async (id: string) => {
  testingId.value = id
  try {
    const result = await llmConfigApi.test(id) as any
    if (result.success) {
      ElMessage.success(`连接成功！模型: ${result.model}`)
    } else {
      ElMessage.error(`连接失败: ${result.error}`)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  } finally {
    testingId.value = ''
  }
}

const deleteConfig = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除此配置？', '确认')
    await llmConfigApi.delete(id)
    ElMessage.success('删除成功')
    configs.value = (await llmConfigApi.list() as any) || []
  } catch {}
}

onMounted(async () => {
  try {
    configs.value = (await llmConfigApi.list() as any) || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.llm-config-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
