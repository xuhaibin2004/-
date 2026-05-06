import api from './index'

export interface AgentConfig {
  id: string
  project_id: string
  name: string
  prompt_template: string
  provider: string
  model: string
  temperature: number
  role_description: string
  is_builtin: boolean
  llm_config_id?: string
  tools?: string[]
  enable_streaming?: boolean
}

export interface CreateAgentRequest {
  name: string
  prompt_template: string
  provider?: string
  model?: string
  temperature?: number
  role_description?: string
  llm_config_id?: string
  tools?: string[]
  enable_streaming?: boolean
}

export const agentApi = {
  list: (projectId: string) => api.get(`/projects/${projectId}/agents`),
  create: (projectId: string, data: CreateAgentRequest) => api.post(`/projects/${projectId}/agents`, data),
  update: (id: string, data: Partial<CreateAgentRequest>) => api.put(`/agents/${id}`, data),
  delete: (id: string) => api.delete(`/agents/${id}`),
  initTemplates: (projectId: string) => api.post(`/projects/${projectId}/agents/init-templates`),
}
