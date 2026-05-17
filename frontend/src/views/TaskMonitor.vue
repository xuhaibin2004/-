<template>
  <div class="task-monitor">
    <h1>任务监控</h1>
    <div v-if="task" class="status-section">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(task.status)" size="large">{{ statusLabel(task.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="迭代次数">{{ task.iteration_count }} / {{ task.max_iterations }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <div v-if="agentStatuses.length > 0">
        <h3>Agent执行状态</h3>
        <el-row :gutter="16">
          <el-col :span="8" v-for="(agent, idx) in agentStatuses" :key="idx">
            <el-card shadow="hover" style="margin-bottom: 16px">
              <div class="agent-status">
                <span class="agent-name">Agent {{ idx + 1 }}</span>
                <el-tag :type="agentStatusType(agent.status)" size="small">{{ agentStatusLabel(agent.status) }}</el-tag>
              </div>
              <div v-if="agent.iteration !== undefined" class="agent-detail">迭代: {{ agent.iteration }}</div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <div v-if="task.status === 'pending_review'">
        <el-alert title="任务已完成，等待审核" type="success" :closable="false" show-icon style="margin-bottom: 16px" />
        <el-button type="primary" size="large" @click="$router.push(`/tasks/${taskId}/review`)">前往审核</el-button>
      </div>
      <div v-else-if="task.status === 'failed'">
        <el-alert title="任务执行失败" type="error" :closable="false" show-icon />
      </div>
      <div v-else>
        <el-alert title="任务执行中，请稍候..." type="info" :closable="false" show-icon />
      </div>

      <el-divider />

      <div class="stream-section">
        <h3>实时生成预览</h3>
        <div class="stream-controls">
          <el-select v-model="selectedAgentConfigId" placeholder="选择Agent" style="width: 300px; margin-right: 12px">
            <el-option v-for="a in agentConfigs" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
          <el-button type="primary" @click="startStream" :disabled="!selectedAgentConfigId || streamActive">开始预览</el-button>
          <el-button @click="stopStream" :disabled="!streamActive">停止</el-button>
        </div>
        <StreamPreview
          v-if="showStreamPreview"
          ref="streamPreviewRef"
          :agent-config-id="selectedAgentConfigId"
          :prompt="task.plot_summary"
          :project-id="task.project_id"
          @done="onStreamDone"
          @error="onStreamError"
        />
      </div>
    </div>
    <el-skeleton v-else :rows="5" animated />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { taskApi, type Task } from '@/api/tasks'
import { agentApi } from '@/api/agents'
import StreamPreview from '@/components/StreamPreview.vue'

const route = useRoute()
const taskId = route.params.id as string

const task = ref<Task | null>(null)
const agentStatuses = ref<any[]>([])
const agentConfigs = ref<any[]>([])
const selectedAgentConfigId = ref('')
const streamActive = ref(false)
const showStreamPreview = ref(false)
const streamPreviewRef = ref<InstanceType<typeof StreamPreview> | null>(null)
let ws: WebSocket | null = null
let pollTimer: any = null

const statusTagType = (status: string) => {
  const map: Record<string, string> = { queued: 'info', generating: 'warning', evaluating: 'warning', pending_review: 'success', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = { queued: '排队中', generating: '生成中', evaluating: '评分中', pending_review: '待审核', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const agentStatusType = (status: string) => {
  const map: Record<string, string> = { pending: 'info', completed: 'success', failed: 'danger', timeout: 'warning' }
  return map[status] || 'info'
}

const agentStatusLabel = (status: string) => {
  const map: Record<string, string> = { pending: '等待中', completed: '已完成', failed: '失败', timeout: '超时' }
  return map[status] || status
}

const fetchStatus = async () => {
  try {
    const data = await taskApi.getStatus(taskId) as any
    if (task.value) {
      task.value.status = data.status
      task.value.iteration_count = data.iteration_count
    }
    agentStatuses.value = data.agent_statuses || []
    if (data.status === 'pending_review' || data.status === 'completed' || data.status === 'failed') {
      if (pollTimer) clearInterval(pollTimer)
    }
  } catch (e) {
    console.error(e)
  }
}

const connectWebSocket = () => {
  const wsUrl = `ws://${window.location.host}/ws/tasks/${taskId}`
  ws = new WebSocket(wsUrl)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (task.value) {
        task.value.status = data.status
        task.value.iteration_count = data.iteration_count || task.value.iteration_count
      }
    } catch {}
  }
  ws.onerror = () => {
    pollTimer = setInterval(fetchStatus, 3000)
  }
}

const startStream = () => {
  if (!selectedAgentConfigId.value) return
  showStreamPreview.value = true
  streamActive.value = true
  setTimeout(() => {
    streamPreviewRef.value?.start()
  }, 100)
}

const stopStream = () => {
  streamPreviewRef.value?.stop()
  streamActive.value = false
}

const onStreamDone = () => {
  streamActive.value = false
  ElMessage.success('生成完成')
}

const onStreamError = (err: string) => {
  streamActive.value = false
  ElMessage.error(`生成失败: ${err}`)
}

onMounted(async () => {
  try {
    task.value = await taskApi.get(taskId) as any
    if (task.value?.project_id) {
      agentConfigs.value = (await agentApi.list(task.value.project_id) as any) || []
    }
  } catch (e) {
    console.error(e)
  }
  fetchStatus()
  connectWebSocket()
  pollTimer = setInterval(fetchStatus, 5000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.task-monitor {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
.agent-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.agent-name {
  font-weight: bold;
}
.agent-detail {
  color: #999;
  font-size: 13px;
}
.stream-section {
  margin-top: 16px;
}
.stream-controls {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}
</style>
