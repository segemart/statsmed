/**
 * API client for Statsmed backend: auth and data endpoints.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getApiUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  return API_BASE_URL;
}

function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('statsmed_token');
}

function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('statsmed_token');
    localStorage.removeItem('statsmed_user');
    window.location.reload();
  }
  return res;
}

// ----- Auth -----

export interface AuthResponse {
  success: boolean;
  message: string;
  user_id: number | null;
  username: string | null;
  token: string | null;
}

export async function registerUser(
  username: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${getApiUrl()}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${getApiUrl()}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

// ----- Tests schema -----

export interface TestInput {
  name: string;
  label: string;
  type: 'column' | 'multi_column' | 'boolean' | 'number' | 'select';
  default?: unknown;
  options?: { value: string; label: string }[];
}

export interface TestSchema {
  id: string;
  label: string;
  description: string;
  inputs: TestInput[];
}

export async function getTests(): Promise<Record<string, TestSchema>> {
  const res = await fetch(`${getApiUrl()}/api/data/tests`);
  if (!res.ok) throw new Error('Failed to load tests');
  return res.json();
}

// ----- Files -----

export interface FileInfo {
  id: number;
  original_filename: string;
  created_at: string;
}

export async function listFiles(): Promise<FileInfo[]> {
  const res = await authFetch(`${getApiUrl()}/api/data/files`);
  if (!res.ok) throw new Error('Failed to list files');
  return res.json();
}

export async function uploadFile(
  file: File,
  csvDelimiter: string = 'comma'
): Promise<FileInfo> {
  const form = new FormData();
  form.append('file', file);
  form.append('csv_delimiter', csvDelimiter);
  const res = await authFetch(`${getApiUrl()}/api/data/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export interface PreviewResult {
  id: number;
  label: string;
  description: string;
  text: string;
  figure: string | null;
  timestamp: string;
}

export interface PreviewResponse {
  file_id: number;
  original_filename: string;
  columns: string[];
  col_types: Record<string, string>;
  preview_html: string;
  results: PreviewResult[];
}

export async function getPreview(fileId: number): Promise<PreviewResponse> {
  const res = await authFetch(`${getApiUrl()}/api/data/files/${fileId}/preview`);
  if (!res.ok) throw new Error('Failed to load preview');
  return res.json();
}

export async function runAnalysis(
  fileId: number,
  testId: string,
  params: Record<string, unknown>
): Promise<PreviewResult> {
  const res = await authFetch(`${getApiUrl()}/api/data/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, test_id: testId, params }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Run failed');
  }
  return res.json();
}

export async function deleteResult(fileId: number, resultId: number): Promise<void> {
  const res = await authFetch(
    `${getApiUrl()}/api/data/files/${fileId}/results/${resultId}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error('Failed to delete result');
}

export async function deleteFile(fileId: number): Promise<void> {
  const res = await authFetch(`${getApiUrl()}/api/data/files/${fileId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete file');
}

export async function downloadPdf(fileId: number): Promise<Blob> {
  const res = await authFetch(`${getApiUrl()}/api/data/files/${fileId}/download-pdf`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to download PDF');
  return res.blob();
}
