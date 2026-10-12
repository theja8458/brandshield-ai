export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface HealthStatus {
  status: string;
  database?: string;
  database_name?: string;
  detail?: string;
  environment?: string;
  service?: string;
}

export async function checkApiHealth(): Promise<HealthStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`);
    const data = await res.json();
    return data;
  } catch {
    return {
      status: 'offline',
      database: 'unreachable',
      detail: 'Cannot connect to backend server',
    };
  }
}
