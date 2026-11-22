import type { ApiResponse, SessionState, KnowledgeSearchResult, KnowledgeDocument, KnowledgeCategory, VoiceSessionConfig, User } from '@/types';

const API_BASE = '/api/v1';

class ApiService {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('sahayak-token') : null;
      const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
          ...options.headers,
        },
        ...options,
      });

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      const isJson = contentType?.includes('application/json');
      const text = await response.text();

      let data: T | null = null;
      let errorMessage: string | null = null;

      if (text) {
        try {
          data = isJson ? JSON.parse(text) : (text as unknown as T);
        } catch {
          // If JSON parsing fails, treat as text error
          errorMessage = text;
        }
      }

      if (!response.ok) {
        if (isJson && data && typeof data === 'object' && 'error' in data) {
          errorMessage = (data as { error: string }).error;
        } else if (!errorMessage) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        return { data: null, error: errorMessage || 'Request failed', success: false };
      }

      return { data, error: null, success: true };
    } catch (error) {
      return { data: null, error: error instanceof Error ? error.message : 'Network error', success: false };
    }
  }

  async createSession(config: VoiceSessionConfig): Promise<ApiResponse<{ sessionId: string; token: string }>> {
    const res = await this.request<{ sessionId?: string; session_id?: string; token: string }>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ config }),
    });
    if (res.success && res.data) {
      return {
        data: {
          sessionId: res.data.sessionId || res.data.session_id || '',
          token: res.data.token,
        },
        error: null,
        success: true,
      };
    }
    return { data: null, error: res.error, success: false };
  }

  async getSession(sessionId: string): Promise<ApiResponse<SessionState>> {
    return this.request<SessionState>(`/sessions/${sessionId}`);
  }

  async endSession(sessionId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/sessions/${sessionId}`, { method: 'DELETE' });
  }

  async searchKnowledge(
    query: string,
    category?: KnowledgeCategory,
    language?: string,
    limit = 10
  ): Promise<ApiResponse<KnowledgeSearchResult>> {
    const params = new URLSearchParams({ query, limit: String(limit) });
    if (category) params.append('category', category);
    if (language) params.append('language', language);
    return this.request<KnowledgeSearchResult>(`/knowledge/search?${params}`);
  }

  async getCategories(): Promise<ApiResponse<KnowledgeCategory[]>> {
    return this.request<KnowledgeCategory[]>('/knowledge/categories');
  }

  async getDocument(id: string): Promise<ApiResponse<KnowledgeDocument>> {
    return this.request<KnowledgeDocument>(`/knowledge/${id}`);
  }

  async submitFeedback(sessionId: string, rating: number, comment?: string): Promise<ApiResponse<void>> {
    return this.request<void>('/feedback', {
      method: 'POST',
      body: JSON.stringify({ sessionId, rating, comment }),
    });
  }

  async googleAuth(
    code: string,
    redirectUri: string
  ): Promise<ApiResponse<{ accessToken: string; tokenType: string; expiresIn: number }>> {
    return this.request<{ accessToken: string; tokenType: string; expiresIn: number }>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ code, redirectUri }),
    });
  }

  async getCurrentUser(token?: string): Promise<ApiResponse<User>> {
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return this.request<User>('/auth/me', { headers });
  }
}

export const apiService = new ApiService();