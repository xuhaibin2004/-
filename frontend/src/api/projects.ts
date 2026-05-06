import api from './index'

export interface Project {
  id: string
  name: string
  genre: string
  style: string
  world_setting: string
  characters: string
  status: string
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  name: string
  genre: string
  style: string
  world_setting?: string
  characters?: string
}

export const projectApi = {
  list: (params?: { page?: number; size?: number }) =>
    api.get('/projects', { params }),
  get: (id: string) => api.get(`/projects/${id}`),
  create: (data: CreateProjectRequest) => api.post('/projects', data),
  update: (id: string, data: Partial<CreateProjectRequest>) => api.put(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
}
