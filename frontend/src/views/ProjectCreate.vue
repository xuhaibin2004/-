<template>
  <div class="project-create">
    <h1>创建项目</h1>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" style="max-width: 600px">
      <el-form-item label="项目名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入项目名称" />
      </el-form-item>
      <el-form-item label="题材" prop="genre">
        <el-input v-model="form.genre" placeholder="如：科幻、悬疑、都市" />
      </el-form-item>
      <el-form-item label="风格" prop="style">
        <el-input v-model="form.style" placeholder="如：轻松幽默、严肃深沉" />
      </el-form-item>
      <el-form-item label="世界观设定">
        <el-input v-model="form.world_setting" type="textarea" :rows="4" placeholder="描述故事的世界观背景" />
      </el-form-item>
      <el-form-item label="角色设定">
        <el-input v-model="form.characters" type="textarea" :rows="4" placeholder="描述主要角色信息" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">创建</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { projectApi } from '@/api/projects'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  name: '',
  genre: '',
  style: '',
  world_setting: '',
  characters: '',
})

const rules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  genre: [{ required: true, message: '请输入题材', trigger: 'blur' }],
  style: [{ required: true, message: '请输入风格', trigger: 'blur' }],
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    const data = await projectApi.create(form) as any
    ElMessage.success('项目创建成功')
    router.push(`/projects/${data.id}`)
  } catch (e) {
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.project-create {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
</style>
