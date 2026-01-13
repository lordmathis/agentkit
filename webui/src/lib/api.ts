// API client for the backend
// Use /api prefix which gets proxied to the backend by Vite
const API_BASE_URL = '/api';

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  model?: string | null;
  system_prompt?: string | null;
  tool_servers?: string[] | null;
  model_params?: Record<string, any> | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sequence: number;
  created_at: string;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
  tool_servers?: any;
  model_params?: any;
}

export interface ChatConfig {
  model: string;
  system_prompt?: string;
  tool_servers?: string[];
  model_params?: Record<string, any>;
}

export interface CreateChatRequest {
  title?: string;
  config: ChatConfig;
}

export interface SendMessageRequest {
  message: string;
  stream?: boolean;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
}

export interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}

export interface ToolServer {
  name: string;
  type: string;
  tools: Tool[];
}

export interface Tool {
  name: string;
  description: string;
  parameters?: any;
}

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Chat endpoints
  async listChats(limit: number = 20): Promise<{ chats: Chat[] }> {
    return this.request(`/chats?limit=${limit}`);
  }

  async getChat(chatId: string): Promise<ChatWithMessages> {
    return this.request(`/chats/${chatId}`);
  }

  async createChat(data: CreateChatRequest): Promise<Chat> {
    return this.request('/chats', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteChat(chatId: string): Promise<{ success: boolean }> {
    return this.request(`/chats/${chatId}`, {
      method: 'DELETE',
    });
  }

  async updateChat(
    chatId: string, 
    data: { title?: string; config?: ChatConfig }
  ): Promise<ChatWithMessages> {
    return this.request(`/chats/${chatId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async sendMessage(
    chatId: string,
    data: SendMessageRequest
  ): Promise<SendMessageResponse> {
    return this.request(`/chats/${chatId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Models and tools endpoints
  async listModels(): Promise<{ object: string; data: Model[] }> {
    return this.request('/models');
  }

  async listTools(): Promise<{ tool_servers: ToolServer[] }> {
    return this.request('/tools');
  }
}

export const api = new ApiClient();
