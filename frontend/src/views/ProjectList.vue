<template>
  <div class="project-list">
    <div class="header">
      <h1>项目管理</h1>
      <el-button type="primary" @click="$router.push('/projects/create')">创建项目</el-button>
    </div>
    <el-input
      v-model="searchQuery"
      placeholder="搜索项目..."
      clearable
      style="margin-bottom: 20px; max-width: 400px"
    />
    <el-row :gutter="20">
      <el-col :span="8" v-for="project in filteredProjects" :key="project.id">
        <el-card shadow="hover" @click="$router.push(`/projects/${project.id}`)" style="cursor: pointer; margin-bottom: 20px">
          <template #header>
            <div class="card-header">
              <span>{{ project.name }}</span>
              <el-tag :type="project.status === 'initialized' ? 'success' : 'info'" size="small">
                {{ project.status === 'initialized' ? '已初始化' : project.status }}
              </el-tag>
            </div>
          </template>
          <p><strong>题材:</strong> {{ project.genre }}</p>
          <p><strong>风格:</strong> {{ project.style }}</p>
          <p v-if="project.world_setting" class="truncated">{{ project.world_setting }}</p>
          <p class="time">{{ new Date(project.created_at).toLocaleString() }}</p>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-if="filteredProjects.length === 0" description="暂无项目" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { projectApi, type Project } from '@/api/projects'

const projects = ref<Project[]>([])
const searchQuery = ref('')

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  const q = searchQuery.value.toLowerCase()
  return projects.value.filter(
    (p) => p.name.toLowerCase().includes(q) || p.genre.toLowerCase().includes(q) || p.style.toLowerCase().includes(q)
  )
})

onMounted(async () => {
  try {
    const data = await projectApi.list() as any
    projects.value = data.items || data || []
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.project-list {
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.truncated {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #999;
  font-size: 13px;
}
.time {
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}
</style>
