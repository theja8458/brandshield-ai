import { apiFetch, setStoredToken, setStoredUser } from './apiClient';
import { LoginResponse, User } from '../types/auth';

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setStoredToken(data.access_token);
  setStoredUser(data.user);
  return data;
}

export async function fetchCurrentUser(): Promise<User> {
  const user = await apiFetch<User>('/api/v1/auth/me');
  setStoredUser(user);
  return user;
}

export async function logoutUser(): Promise<void> {
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
  } catch (err) {
    // Proceed with client logout even if server unreachable
    console.debug('Server logout error:', err);
  } finally {
    setStoredToken(null);
  }
}

export async function createAnalystUser(userIn: {
  email: string;
  password: string;
  role: 'admin' | 'analyst';
}): Promise<User> {
  return apiFetch<User>('/api/v1/auth/users', {
    method: 'POST',
    body: JSON.stringify(userIn),
  });
}

export async function listUsers(): Promise<User[]> {
  return apiFetch<User[]>('/api/v1/auth/users');
}
