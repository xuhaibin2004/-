<template>
  <div class="agent-config">
    <div class="header">
      <h1>Agent配置</h1>
      <el-button type="primary" @click="showAddDialog = true">添加Agent</el-button>
    </div>

    <el-table :data="agents" stripe>
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column prop="provider" label="Provider" width="120" />
      <el-table-column prop="model" label="模型" width="180" />
      <el-table-column prop="temperature" label="温度" width="80" />
      <el-table-column prop="role_description" label="角色描述" show-overflow-tooltip />
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
        <el-form-item label="Provider">
          <el-select v-model="agentForm.provider">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="agentForm.model" placeholder="如: gpt-4o, gpt-4o-mini, claude-sonnet-4-20250514" />
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
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAgent" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, type AgentConfig } from '@/api/agents'

const route = useRoute()
const projectId = route.params.id as string

const agents = ref<AgentConfig[]>([])
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
}

const agentForm = reactive({ ...defaultForm })

const editAgent = (agent: AgentConfig) => {
  editingAgent.value = agent
  Object.assign(agentForm, {
    name: agent.name,
    prompt_template: agent.prompt_template,
    provider: agent.provider,
    model: agent.model,
    temperature: agent.temperature,
    role_description: agent.role_description,
  })
  showAddDialog.value = true
}

const saveAgent = async () => {
  saving.value = true
  try {
    if (editingAgent.value) {
      await agentApi.update(editingAgent.value.id, agentForm)
      ElMessage.success('更新成功')
    } else {
      await agentApi.create(projectId, agentForm)
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
    agents.value = (await agentApi.list(projectId) as any) || []
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
