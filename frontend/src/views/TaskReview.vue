<template>
  <div class="task-review" v-if="reviewData">
    <h1>内容审核</h1>

    <el-descriptions :column="3" border style="margin-bottom: 20px">
      <el-descriptions-item label="任务状态">
        <el-tag :type="statusTagType(reviewData.task.status)">{{ statusLabel(reviewData.task.status) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="迭代次数">{{ reviewData.task.iteration_count }}</el-descriptions-item>
      <el-descriptions-item label="AI率阈值">{{ reviewData.task.ai_rate_threshold }}</el-descriptions-item>
    </el-descriptions>

    <el-divider content-position="left">生成结果对比</el-divider>

    <div class="results-grid">
      <el-card
        v-for="result in validResults"
        :key="result.id"
        :class="{ 'recommended': result.is_recommended, 'selected': result.is_selected }"
        shadow="hover"
      >
        <template #header>
          <div class="result-header">
            <span>{{ result.agent_config_id ? 'Agent' : '未知' }}</span>
            <div>
              <el-tag v-if="result.is_recommended" type="success" size="small">推荐</el-tag>
              <el-tag v-if="result.is_selected" type="warning" size="small">已选</el-tag>
              <el-tag v-if="result.is_edited" type="info" size="small">已编辑</el-tag>
            </div>
          </div>
        </template>

        <div class="result-content" @click="selectResult(result)">
          <div class="content-text">{{ result.content }}</div>
        </div>

        <div v-if="result.score" class="score-section">
          <el-row :gutter="8">
            <el-col :span="8">
              <div class="score-item">
                <div class="score-label">AI率</div>
                <div class="score-value" :class="{ 'good': result.score.ai_rate_score < 50, 'bad': result.score.ai_rate_score > 70 }">
                  {{ result.score.ai_rate_score.toFixed(1) }}
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="score-item">
                <div class="score-label">创意性</div>
                <div class="score-value">{{ result.score.creativity_score.toFixed(1) }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="score-item">
                <div class="score-label">综合</div>
                <div class="score-value">{{ result.score.overall_score.toFixed(1) }}</div>
              </div>
            </el-col>
          </el-row>
          <div v-if="result.score.external_ai_rate !== null && result.score.external_ai_rate !== undefined" class="external-score">
            GPTZero AI率: {{ result.score.external_ai_rate.toFixed(1) }}%
          </div>
        </div>

        <div class="result-actions">
          <el-button size="small" @click="openEditor(result)">编辑</el-button>
          <el-button size="small" type="primary" @click="openFeedback(result)">反馈</el-button>
          <el-button size="small" type="success" @click="finalizeResult(result)">选为最终</el-button>
          <el-button size="small" type="warning" @click="openStreamRegenerate(result)">流式重新生成</el-button>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showEditor" title="编辑内容" width="700px">
      <el-input v-model="editContent" type="textarea" :rows="15" />
      <template #footer>
        <el-button @click="showEditor = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="editing">保存</el-button>
        <el-button type="warning" @click="recheckAiRate" :loading="rechecking">重新检测AI率</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showFeedback" title="提交反馈" width="500px">
      <el-form label-width="100px">
        <el-form-item label="问题类型">
          <el-checkbox-group v-model="feedbackForm.problem_types">
            <el-checkbox label="AI味重" value="ai_taste" />
            <el-checkbox label="内容空洞" value="hollow" />
            <el-checkbox label="逻辑不通" value="illogical" />
            <el-checkbox label="风格不符" value="style_mismatch" />
            <el-checkbox label="缺乏细节" value="lack_detail" />
            <el-checkbox label="重复啰嗦" value="repetitive" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="feedbackForm.description" type="textarea" :rows="4" placeholder="请描述具体问题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFeedback = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback" :loading="submittingFeedback">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showStreamRegen" title="流式重新生成" width="700px">
      <StreamPreview
        v-if="showStreamRegen"
        ref="streamPreviewRef"
        :agent-config-id="streamRegenAgentId"
        :prompt="reviewData?.task?.plot_summary || ''"
        :project-id="reviewData?.task?.project_id"
        @done="onStreamRegenDone"
        @error="onStreamRegenError"
      />
    </el-dialog>
  </div>
  <el-skeleton v-else :rows="10" animated />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/index'
import StreamPreview from '@/components/StreamPreview.vue'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const reviewData = ref<any>(null)
const showEditor = ref(false)
const showFeedback = ref(false)
const showStreamRegen = ref(false)
const streamRegenAgentId = ref('')
const streamPreviewRef = ref<InstanceType<typeof StreamPreview> | null>(null)
const editing = ref(false)
const rechecking = ref(false)
const submittingFeedback = ref(false)
const editContent = ref('')
const editingResultId = ref('')
const feedbackResultId = ref('')

const feedbackForm = ref({
  problem_types: [] as string[],
  description: '',
})

const validResults = computed(() => {
  if (!reviewData.value) return []
  return reviewData.value.results.filter((r: any) => r.status === 'completed' && r.content)
})

const statusTagType = (status: string) => {
  const map: Record<string, string> = { pending_review: 'success', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = { pending_review: '待审核', completed: '已完成', failed: '失败' }
  return map[status] || status
}

const openEditor = (result: any) => {
  editingResultId.value = result.id
  editContent.value = result.content
  showEditor.value = true
}

const saveEdit = async () => {
  editing.value = true
  try {
    await api.put(`/generation-results/${editingResultId.value}`, { content: editContent.value })
    ElMessage.success('内容已保存')
    showEditor.value = false
    await fetchReview()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    editing.value = false
  }
}

const recheckAiRate = async () => {
  rechecking.value = true
  try {
    await api.put(`/generation-results/${editingResultId.value}`, { content: editContent.value })
    const result = await api.post(`/generation-results/${editingResultId.value}/recheck`)
    ElMessage.success(`AI率: ${(result as any).ai_rate_score?.toFixed(1) || '未知'}`)
    await fetchReview()
  } catch (e) {
    ElMessage.error('检测失败')
  } finally {
    rechecking.value = false
  }
}

const openFeedback = (result: any) => {
  feedbackResultId.value = result.id
  feedbackForm.value = { problem_types: [], description: '' }
  showFeedback.value = true
}

const submitFeedback = async () => {
  if (feedbackForm.value.problem_types.length === 0 && !feedbackForm.value.description) {
    ElMessage.warning('请至少选择一个问题类型或填写描述')
    return
  }
  submittingFeedback.value = true
  try {
    await api.post(`/generation-results/${feedbackResultId.value}/feedback`, feedbackForm.value)
    ElMessage.success('反馈已提交')
    showFeedback.value = false
  } catch (e) {
    ElMessage.error('提交失败')
  } finally {
    submittingFeedback.value = false
  }
}

const finalizeResult = async (result: any) => {
  try {
    await ElMessageBox.confirm('确定选择此内容作为最终结果？', '确认')
    await api.post(`/tasks/${taskId}/finalize`, { result_id: result.id })
    ElMessage.success('已选择最终结果')
    router.push(`/projects/${reviewData.value.task.project_id}`)
  } catch {}
}

const selectResult = (result: any) => {}

const openStreamRegenerate = (result: any) => {
  streamRegenAgentId.value = result.agent_config_id || ''
  showStreamRegen.value = true
  setTimeout(() => {
    streamPreviewRef.value?.start()
  }, 100)
}

const onStreamRegenDone = () => {
  ElMessage.success('重新生成完成')
  fetchReview()
}

const onStreamRegenError = (err: string) => {
  ElMessage.error(`重新生成失败: ${err}`)
}

const fetchReview = async () => {
  try {
    reviewData.value = await api.get(`/tasks/${taskId}/review`) as any
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchReview)
</script>

<style scoped>
.task-review {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}
.recommended {
  border: 2px solid #67c23a;
}
.selected {
  border: 2px solid #e6a23c;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-content {
  cursor: pointer;
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 12px;
}
.content-text {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 14px;
}
.score-section {
  padding: 12px 0;
  border-top: 1px solid #eee;
}
.score-item {
  text-align: center;
}
.score-label {
  font-size: 12px;
  color: #999;
}
.score-value {
  font-size: 20px;
  font-weight: bold;
}
.score-value.good {
  color: #67c23a;
}
.score-value.bad {
  color: #f56c6c;
}
.external-score {
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
.result-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}
</style>
