import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskApi, type Task } from '@/api/tasks'

export const useTaskStore = defineStore('task', () => {
  const currentTask = ref<Task | null>(null)
  const loading = ref(false)

  async function fetchTask(id: string) {
    loading.value = true
    try {
      currentTask.value = await taskApi.get(id) as any
    } finally {
      loading.value = false
    }
  }

  return { currentTask, loading, fetchTask }
})
