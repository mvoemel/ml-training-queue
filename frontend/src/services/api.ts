import axios from "axios";

const API_URL = "/api";

const api = axios.create({
  baseURL: API_URL,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface Job {
  id: number;
  name: string;
  user_id: number;
  status: string;
  gpu_id: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  container_id: string | null;
  error_log: string | null;
}

export interface GPU {
  id: number;
  name: string;
  memory: number;
  available: boolean;
}

export interface GPUStats {
  gpu_id: number;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
}

export const authAPI = {
  register: (username: string, password: string) =>
    api.post("/auth/register", { username, password }),

  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),

  checkRegistration: () => api.get("/auth/check"),
};

export const userAPI = {
  getUsers: () => api.get<User[]>("/users"),
  createUser: (username: string, password: string) =>
    api.post<User>("/users", { username, password }),
  deleteUser: (userId: number) => api.delete(`/users/${userId}`),
};

export const gpuAPI = {
  getGPUs: () => api.get<GPU[]>("/gpus"),
  getGPUStats: (gpuId: number) => api.get<GPUStats>(`/gpus/${gpuId}/stats`),
};

export const jobAPI = {
  getJobs: () => api.get<Job[]>("/jobs"),
  getJob: (jobId: number) => api.get<Job>(`/jobs/${jobId}`),

  createJob: (formData: FormData, onProgress?: (progress: number) => void) =>
    api.post<Job>("/jobs", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    }),

  cancelJob: (jobId: number) => api.delete(`/jobs/${jobId}`),
  getLogs: (jobId: number) => api.get<{ logs: string }>(`/jobs/${jobId}/logs`),
  downloadOutput: (jobId: number) => {
    window.open(`${API_URL}/jobs/${jobId}/download`, "_blank");
  },
};

export const createWebSocket = (jobId: number) => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/jobs/${jobId}`);
};

export default api;
