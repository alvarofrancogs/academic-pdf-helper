import { JobStatusResponse, ProcessResponse, SessionStatus } from '../types';

const BASE_URL = '/api';

export const api = {
  async getHealth() {
    const res = await fetch(`${BASE_URL}/health`);
    if (!res.ok) throw new Error('Error al conectar con el servidor.');
    return res.json();
  },

  async getSessionStatus(): Promise<SessionStatus> {
    const res = await fetch(`${BASE_URL}/session/status`);
    if (!res.ok) throw new Error('Error al consultar estado de sesión.');
    return res.json();
  },

  async startSession(): Promise<SessionStatus> {
    const res = await fetch(`${BASE_URL}/session/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error al iniciar sesión en el navegador.');
    }
    return res.json();
  },

  async switchSession(): Promise<SessionStatus> {
    const res = await fetch(`${BASE_URL}/session/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error al cambiar sesión en el navegador.');
    }
    return res.json();
  },

  async processDocument(url: string): Promise<ProcessResponse> {
    const res = await fetch(`${BASE_URL}/document/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al solicitar el procesamiento del documento.');
    }
    return res.json();
  },

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${BASE_URL}/document/status/${jobId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al obtener estado del proceso.');
    }
    return res.json();
  },

  getDownloadUrl(jobId: string): string {
    return `${BASE_URL}/document/download/${jobId}`;
  },

  getPreviewUrl(jobId: string): string {
    return `${BASE_URL}/document/download/${jobId}?inline=true`;
  },
};

