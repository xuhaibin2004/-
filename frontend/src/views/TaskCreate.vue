<template>
  <div class="task-create">
    <h1>创建生成任务</h1>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="120px" style="max-width: 700px">
      <el-form-item label="剧情概要" prop="plot_summary">
        <el-input v-model="form.plot_summary" type="textarea" :rows="6" placeholder="请输入剧情概要，Agent将基于此生成正文内容" />
      </el-form-item>
      <el-form-item label="Agent数量" prop="agent_count">
        <el-slider v-model="form.agent_count" :min="1" :max="5" :step="1" show-input :show-input-controls="false" />
      </el-form-item>
      <el-collapse>
        <el-collapse-item title="高级选项" name="advanced">
          <el-form-item label="最大迭代次数">
            <el-input-number v-model="form.max_iterations" :min="1" :max="10" />
          </el-form-item>
          <el-form-item label="AI率阈值">
            <el-input-number v-model="form.ai_rate_threshold" :min="0" :max="100" :step="5" />
            <div style="color: #999; font-size: 12px; margin-top: 4px">低于此阈值时停止迭代（越低越自然）</div>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>
      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">提交任务</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { taskApi } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const projectId = route.params.id as string
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  plot_summary: '',
  agent_count: 3,
  max_iterations: 3,
  ai_rate_threshold: 70,
})

const rules = {
  plot_summary: [{ required: true, message: '请输入剧情概要', trigger: 'blur' }],
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    const data = await taskApi.create(projectId, form) as any
    ElMessage.success('任务已提交')
    router.push(`/tasks/${data.id}/monitor`)
  } catch (e) {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.task-create {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
</style>
