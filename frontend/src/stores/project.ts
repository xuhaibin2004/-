import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectApi, type Project } from '@/api/projects'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      const data = await projectApi.list() as any
      projects.value = data.items || data
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: string) {
    loading.value = true
    try {
      currentProject.value = await projectApi.get(id) as any
    } finally {
      loading.value = false
    }
  }

  return { projects, currentProject, loading, fetchProjects, fetchProject }
})
