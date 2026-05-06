<template>
  <div class="stream-preview">
    <div class="preview-header">
      <span class="status-dot" :class="{ active: isStreaming, done: isDone }"></span>
      <span>{{ statusText }}</span>
      <el-button v-if="isStreaming" size="small" type="danger" @click="stop">停止</el-button>
    </div>
    <div class="preview-content" ref="contentRef">
      <div v-for="(event, idx) in events" :key="idx" class="event-item">
        <div v-if="event.type === 'content'" class="content-text">{{ event.data }}</div>
        <div v-else-if="event.type === 'tool_call_start'" class="tool-call-item">
          <el-tag type="warning" size="small">🔧 调用工具: {{ event.data.name }}</el-tag>
        </div>
        <div v-else-if="event.type === 'tool_execution'" class="tool-call-item">
          <el-tag type="info" size="small">⏳ 执行中: {{ event.data.name }}</el-tag>
        </div>
        <div v-else-if="event.type === 'tool_result'" class="tool-result-item">
          <el-tag type="success" size="small">✅ {{ event.data.name }} 完成</el-tag>
        </div>
        <div v-else-if="event.type === 'error'" class="error-item">
          <el-tag type="danger" size="small">❌ 错误: {{ event.data }}</el-tag>
        </div>
      </div>
      <span v-if="isStreaming" class="cursor-blink">▌</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'

const props = defineProps<{
  agentConfigId: string
  prompt: string
  projectId?: string
}>()

const emit = defineEmits<{
  (e: 'done', content: string): void
  (e: 'error', error: string): void
}>()

const events = ref<{ type: string; data: any }[]>([])
const isStreaming = ref(false)
const isDone = ref(false)
const contentRef = ref<HTMLElement | null>(null)
let eventSource: EventSource | null = null
let fullContent = ''

const statusText = computed(() => {
  if (isDone.value) return '生成完成'
  if (isStreaming.value) return '生成中...'
  return '等待中'
})

const start = () => {
  if (!props.agentConfigId || !props.prompt) return
  events.value = []
  fullContent = ''
  isStreaming.value = true
  isDone.value = false

  const params = new URLSearchParams({
    agent_config_id: props.agentConfigId,
    prompt: props.prompt,
  })
  if (props.projectId) {
    params.append('project_id', props.projectId)
  }

  eventSource = new EventSource(`/api/stream/generate?${params.toString()}`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'content') {
        fullContent += data.data
        events.value.push({ type: 'content', data: data.data })
      } else if (data.type === 'tool_call_start' || data.type === 'tool_execution' || data.type === 'tool_result') {
        events.value.push({ type: data.type, data: data.data })
      } else if (data.type === 'done') {
        isStreaming.value = false
        isDone.value = true
        eventSource?.close()
        eventSource = null
        emit('done', fullContent)
      } else if (data.type === 'error') {
        isStreaming.value = false
        isDone.value = true
        events.value.push({ type: 'error', data: data.data })
        eventSource?.close()
        eventSource = null
        emit('error', data.data)
      }
      scrollToBottom()
    } catch {}
  }

  eventSource.onerror = () => {
    isStreaming.value = false
    isDone.value = true
    eventSource?.close()
    eventSource = null
    if (!isDone.value) {
      emit('error', 'Connection lost')
    }
  }
}

const stop = () => {
  eventSource?.close()
  eventSource = null
  isStreaming.value = false
  isDone.value = true
}

const scrollToBottom = () => {
  if (contentRef.value) {
    contentRef.value.scrollTop = contentRef.value.scrollHeight
  }
}

onUnmounted(() => {
  eventSource?.close()
})

defineExpose({ start, stop })
</script>

<style scoped>
.stream-preview {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}
.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}
.status-dot.active {
  background: #e6a23c;
  animation: blink 1s infinite;
}
.status-dot.done {
  background: #67c23a;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.preview-content {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 14px;
}
.content-text {
  display: inline;
}
.tool-call-item, .tool-result-item, .error-item {
  margin: 4px 0;
}
.cursor-blink {
  animation: blink 0.8s infinite;
  color: #409eff;
}
</style>
