import api from './index'

export interface LLMConfig {
  id: string
  name: string
  provider_type: string
  api_key: string
  base_url: string
  available_models: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LLMConfigBrief {
  id: string
  name: string
  provider_type: string
  available_models: string[]
  is_active: boolean
}

export interface CreateLLMConfigRequest {
  name: string
  provider_type: string
  api_key: string
  base_url?: string
  available_models: string[]
  is_active?: boolean
}

export const llmConfigApi = {
  list: () => api.get('/llm-configs'),
  brief: () => api.get('/llm-configs/brief'),
  get: (id: string) => api.get(`/llm-configs/${id}`),
  create: (data: CreateLLMConfigRequest) => api.post('/llm-configs', data),
  update: (id: string, data: Partial<CreateLLMConfigRequest>) => api.put(`/llm-configs/${id}`, data),
  delete: (id: string) => api.delete(`/llm-configs/${id}`),
  test: (id: string) => api.post(`/llm-configs/${id}/test`),
}
