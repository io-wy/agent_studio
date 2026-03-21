import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8002';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Tenant {
  id: string;
  name: string;
  status: string;
  quota_gpuHours: number;
  quota_storage_gb: number;
  quota_deployments: number;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  status: string;
  namespace: string;
  quota_gpuHours: number;
  quota_storage_gb: number;
  quota_deployments: number;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: string;
  data_format: string;
  storage_prefix: string;
  created_at: string;
  updated_at: string;
}

export interface TrainingJob {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: string;
  base_model: string;
  training_type: string;
  created_at: string;
}

export interface Model {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: string;
  base_model: string;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: string;
  system_prompt?: string;
  tools?: string;
  model_binding?: string;
  created_at: string;
  updated_at: string;
}

// API Functions
export const apiService = {
  // Tenants
  async getTenants(): Promise<Tenant[]> {
    const res = await api.get('/api/v1/tenants');
    return res.data;
  },
  async createTenant(data: { name: string; quota_gpuHours?: number }): Promise<Tenant> {
    const res = await api.post('/api/v1/tenants', data);
    return res.data;
  },
  async getTenant(id: string): Promise<Tenant> {
    const res = await api.get(`/api/v1/tenants/${id}`);
    return res.data;
  },
  async deleteTenant(id: string): Promise<void> {
    await api.delete(`/api/v1/tenants/${id}`);
  },

  // Projects
  async getProjects(tenantId: string): Promise<Project[]> {
    const res = await api.get(`/api/v1/projects?tenant_id=${tenantId}`);
    return res.data;
  },
  async createProject(data: { tenant_id: string; name: string; description?: string }): Promise<Project> {
    const res = await api.post('/api/v1/projects', data);
    return res.data;
  },
  async deleteProject(id: string): Promise<void> {
    await api.delete(`/api/v1/projects/${id}`);
  },

  // Datasets
  async getDatasets(projectId: string): Promise<Dataset[]> {
    const res = await api.get(`/api/v1/datasets?project_id=${projectId}`);
    return res.data;
  },
  async createDataset(data: { project_id: string; name: string; data_format: string }): Promise<Dataset> {
    const res = await api.post('/api/v1/datasets', data);
    return res.data;
  },
  async deleteDataset(id: string): Promise<void> {
    await api.delete(`/api/v1/datasets/${id}`);
  },

  // Training Jobs
  async getTrainingJobs(projectId: string): Promise<TrainingJob[]> {
    const res = await api.get(`/api/v1/training-jobs?project_id=${projectId}`);
    return res.data;
  },
  async createTrainingJob(data: { project_id: string; name: string; base_model: string; training_type: string }): Promise<TrainingJob> {
    const res = await api.post('/api/v1/training-jobs', data);
    return res.data;
  },

  // Models
  async getModels(projectId: string): Promise<Model[]> {
    const res = await api.get(`/api/v1/models?project_id=${projectId}`);
    return res.data;
  },
  async createModel(data: { project_id: string; name: string; base_model: string }): Promise<Model> {
    const res = await api.post('/api/v1/models', data);
    return res.data;
  },

  // Agents
  async getAgents(projectId: string): Promise<Agent[]> {
    const res = await api.get(`/api/v1/agents?project_id=${projectId}`);
    return res.data;
  },
  async createAgent(data: { project_id: string; name: string; system_prompt?: string }): Promise<Agent> {
    const res = await api.post('/api/v1/agents', data);
    return res.data;
  },
};
