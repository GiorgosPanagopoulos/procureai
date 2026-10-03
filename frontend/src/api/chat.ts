import { API_BASE, apiJson } from './client';
import type { AgentResponse, Bid, Supplier } from '../types';

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function sendChatMessage(message: string, conversationId: string | null): Promise<AgentResponse> {
  return apiJson<AgentResponse>('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    timeoutMs: 60000,
  });
}

export async function uploadDocument(file: File): Promise<{ message?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return apiJson('/upload', { method: 'POST', body: formData, timeoutMs: 20000 }, 'Upload failed');
}

export async function fetchSuppliers(): Promise<Supplier[]> {
  return apiJson<Supplier[]>('/suppliers', {}, 'Failed to fetch suppliers');
}

export async function fetchBids(): Promise<Bid[]> {
  return apiJson<Bid[]>('/bids', {}, 'Failed to fetch bids');
}
