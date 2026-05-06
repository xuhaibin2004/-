import api from './index'

export interface Task {
  id: string
  project_id: string
  plot_summary: string
  status: string
  iteration_count: number
  max_iterations: number
  ai_rate_threshold: number
  created_at: string
  updated_at: string
}

export interface CreateTaskRequest {
  plot_summary: string
  agent_count?: number
  max_iterations?: number
  ai_rate_threshold?: number
}

export const taskApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/tasks`),
  get: (id: string) => api.get(`/tasks/${id}`),
  create: (projectId: string, data: CreateTaskRequest) => api.post(`/projects/${projectId}/tasks`, data),
  getStatus: (id: string) => api.get(`/tasks/${id}/status`),
}
