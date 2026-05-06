<template>
  <div class="project-detail" v-if="project">
    <div class="header">
      <div>
        <h1>{{ project.name }}</h1>
        <el-tag type="success" size="small">{{ project.status === 'initialized' ? '已初始化' : project.status }}</el-tag>
      </div>
      <el-button type="primary" @click="$router.push(`/projects/${projectId}/tasks/create`)">创建任务</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本信息" name="info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="题材">{{ project.genre }}</el-descriptions-item>
          <el-descriptions-item label="风格">{{ project.style }}</el-descriptions-item>
          <el-descriptions-item label="世界观" :span="2">{{ project.world_setting || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="角色" :span="2">{{ project.characters || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ new Date(project.created_at).toLocaleString() }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <el-tab-pane label="Agent配置" name="agents">
        <div style="margin-bottom: 16px">
          <el-button @click="initTemplates" :loading="initLoading">初始化预设模板</el-button>
          <el-button type="primary" @click="$router.push(`/projects/${projectId}/agents`)">配置Agent</el-button>
        </div>
        <el-table :data="agents" stripe>
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="provider" label="Provider" width="120" />
          <el-table-column prop="model" label="模型" width="150" />
          <el-table-column prop="temperature" label="温度" width="80" />
          <el-table-column prop="is_builtin" label="预设" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_builtin ? 'info' : 'success'" size="small">
                {{ row.is_builtin ? '是' : '自定义' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="任务历史" name="tasks">
        <el-table :data="tasks" stripe>
          <el-table-column prop="plot_summary" label="剧情概要" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="iteration_count" label="迭代次数" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button v-if="row.status === 'pending_review'" type="primary" size="small" @click="$router.push(`/tasks/${row.id}/review`)">审核</el-button>
              <el-button v-else-if="['generating', 'evaluating'].includes(row.status)" type="info" size="small" @click="$router.push(`/tasks/${row.id}/monitor`)">监控</el-button>
              <el-button v-else size="small" @click="$router.push(`/tasks/${row.id}/review`)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi, type Project } from '@/api/projects'
import { agentApi, type AgentConfig } from '@/api/agents'
import { taskApi, type Task } from '@/api/tasks'

const route = useRoute()
const projectId = route.params.id as string

const project = ref<Project | null>(null)
const agents = ref<AgentConfig[]>([])
const tasks = ref<Task[]>([])
const activeTab = ref('info')
const initLoading = ref(false)

const statusTagType = (status: string) => {
  const map: Record<string, string> = { queued: 'info', generating: 'warning', evaluating: 'warning', pending_review: 'success', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = { queued: '排队中', generating: '生成中', evaluating: '评分中', pending_review: '待审核', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const initTemplates = async () => {
  initLoading.value = true
  try {
    const data = await agentApi.initTemplates(projectId) as any
    agents.value = data || []
    ElMessage.success('预设模板初始化成功')
  } catch (e) {
    ElMessage.error('初始化失败')
  } finally {
    initLoading.value = false
  }
}

onMounted(async () => {
  try {
    project.value = await projectApi.get(projectId) as any
    agents.value = (await agentApi.list(projectId) as any) || []
    const taskData = await taskApi.list(projectId) as any
    tasks.value = taskData.items || taskData || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.project-detail {
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
