<template>
  <div class="agent-config">
    <div class="header">
      <h1>Agent配置</h1>
      <el-button type="primary" @click="showAddDialog = true">添加Agent</el-button>
    </div>

    <el-table :data="agents" stripe>
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="LLM配置" width="180">
        <template #default="{ row }">
          <span v-if="row.llm_config_id">{{ getLLMConfigName(row.llm_config_id) }}</span>
          <span v-else>{{ row.provider }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="model" label="模型" width="180" />
      <el-table-column prop="temperature" label="温度" width="80" />
      <el-table-column label="工具" width="120">
        <template #default="{ row }">
          <el-tag v-for="t in (row.tools || [])" :key="t" size="small" style="margin: 2px">{{ t }}</el-tag>
          <span v-if="!row.tools || row.tools.length === 0">-</span>
        </template>
      </el-table-column>
      <el-table-column label="流式" width="60">
        <template #default="{ row }">
          <el-tag :type="row.enable_streaming ? 'success' : 'info'" size="small">
            {{ row.enable_streaming ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="editAgent(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteAgent(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" :title="editingAgent ? '编辑Agent' : '添加Agent'" width="700px">
      <el-form :model="agentForm" label-width="120px">
        <el-form-item label="名称">
          <el-input v-model="agentForm.name" placeholder="Agent名称" />
        </el-form-item>
        <el-form-item label="LLM配置">
          <el-select v-model="agentForm.llm_config_id" placeholder="选择LLM配置" clearable style="width: 100%" @change="onLLMConfigChange">
            <el-option v-for="cfg in llmConfigs" :key="cfg.id" :label="cfg.name" :value="cfg.id" />
          </el-select>
          <div v-if="!agentForm.llm_config_id" style="margin-top: 8px">
            <el-select v-model="agentForm.provider" style="width: 48%; margin-right: 4%">
              <el-option label="OpenAI" value="openai" />
              <el-option label="Anthropic" value="anthropic" />
              <el-option label="OpenAI 兼容" value="openai_compatible" />
            </el-select>
            <el-input v-model="agentForm.model" placeholder="模型名称" style="width: 48%" />
          </div>
        </el-form-item>
        <el-form-item v-if="agentForm.llm_config_id" label="模型">
          <el-select v-model="agentForm.model" style="width: 100%">
            <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="温度">
          <el-slider v-model="agentForm.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="角色描述">
          <el-input v-model="agentForm.role_description" type="textarea" :rows="2" placeholder="描述Agent的角色定位" />
        </el-form-item>
        <el-form-item label="Prompt模板">
          <el-input v-model="agentForm.prompt_template" type="textarea" :rows="8" placeholder="可用变量: {plot_summary}, {memory_context}, {world_setting}, {characters}, {style}, {genre}, {feedback}" />
        </el-form-item>
        <el-form-item label="绑定工具">
          <el-checkbox-group v-model="agentForm.tools">
            <el-checkbox v-for="tool in toolList" :key="tool.name" :label="tool.name" :value="tool.name">
              {{ tool.name }}
              <span style="color: #999; font-size: 12px">- {{ tool.description }}</span>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="启用流式输出">
          <el-switch v-model="agentForm.enable_streaming" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAgent" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, type AgentConfig } from '@/api/agents'
import { llmConfigApi, type LLMConfigBrief } from '@/api/llmConfigs'
import { toolApi, type ToolDefinition } from '@/api/tools'

const route = useRoute()
const projectId = route.params.id as string

const agents = ref<AgentConfig[]>([])
const llmConfigs = ref<LLMConfigBrief[]>([])
const toolList = ref<ToolDefinition[]>([])
const showAddDialog = ref(false)
const saving = ref(false)
const editingAgent = ref<AgentConfig | null>(null)

const defaultForm = {
  name: '',
  prompt_template: '',
  provider: 'openai',
  model: 'gpt-4o-mini',
  temperature: 0.7,
  role_description: '',
  llm_config_id: '' as string,
  tools: [] as string[],
  enable_streaming: false,
}

const agentForm = reactive({ ...defaultForm })

const availableModels = computed(() => {
  if (!agentForm.llm_config_id) return []
  const cfg = llmConfigs.value.find(c => c.id === agentForm.llm_config_id)
  return cfg?.available_models || []
})

const getLLMConfigName = (id: string) => {
  const cfg = llmConfigs.value.find(c => c.id === id)
  return cfg?.name || id
}

const onLLMConfigChange = (configId: string) => {
  if (configId) {
    const cfg = llmConfigs.value.find(c => c.id === configId)
    if (cfg) {
      agentForm.provider = cfg.provider_type
      if (cfg.available_models.length > 0) {
        agentForm.model = cfg.available_models[0]
      }
    }
  }
}

const editAgent = (agent: any) => {
  editingAgent.value = agent
  Object.assign(agentForm, {
    name: agent.name,
    prompt_template: agent.prompt_template,
    provider: agent.provider,
    model: agent.model,
    temperature: agent.temperature,
    role_description: agent.role_description,
    llm_config_id: agent.llm_config_id || '',
    tools: agent.tools || [],
    enable_streaming: agent.enable_streaming || false,
  })
  showAddDialog.value = true
}

const saveAgent = async () => {
  saving.value = true
  try {
    const data: any = { ...agentForm }
    if (!data.llm_config_id) {
      delete data.llm_config_id
    }
    if (editingAgent.value) {
      await agentApi.update(editingAgent.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await agentApi.create(projectId, data)
      ElMessage.success('添加成功')
    }
    showAddDialog.value = false
    editingAgent.value = null
    Object.assign(agentForm, defaultForm)
    agents.value = (await agentApi.list(projectId) as any) || []
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const deleteAgent = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除此Agent配置？', '确认')
    await agentApi.delete(id)
    ElMessage.success('删除成功')
    agents.value = (await agentApi.list(projectId) as any) || []
  } catch {}
}

onMounted(async () => {
  try {
    const [agentData, llmData, toolData] = await Promise.all([
      agentApi.list(projectId),
      llmConfigApi.brief(),
      toolApi.list(),
    ])
    agents.value = (agentData as any) || []
    llmConfigs.value = (llmData as any) || []
    toolList.value = (toolData as any) || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.agent-config {
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
