import api from './index'

export interface ToolDefinition {
  id: string
  name: string
  description: string
  parameters_schema: Record<string, any>
  implementation_type: string
  implementation_config: Record<string, any>
  is_active: boolean
  created_at: string
}

export interface CreateToolRequest {
  name: string
  description?: string
  parameters_schema?: Record<string, any>
  implementation_type?: string
  implementation_config?: Record<string, any>
  is_active?: boolean
}

export const toolApi = {
  list: () => api.get('/tools'),
  get: (id: string) => api.get(`/tools/${id}`),
  create: (data: CreateToolRequest) => api.post('/tools', data),
  update: (id: string, data: Partial<CreateToolRequest>) => api.put(`/tools/${id}`, data),
  delete: (id: string) => api.delete(`/tools/${id}`),
}
