// API client for the backend
// Use /api prefix which gets proxied to the backend by Vite
//
// API Structure:
// - /api/chats/* - Chat management and messaging
// - /api/config/* - Configuration (models, chatbots, providers, default settings)
// - /api/github/* - GitHub integration
// - /api/media/* - Media processing (transcription, etc.)
// - /api/skills/* - Skills management
// - /api/tools/* - Tool servers and tools
const API_BASE_URL = '/api';

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  model?: string | null;
  system_prompt?: string | null;
  tool_servers?: string[] | null;
  model_params?: ModelParams | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  reasoning_content?: string | null;
  tool_calls?: Array<{
    name: string;
    arguments: Record<string, any>;
  }> | null;
  sequence: number;
  created_at: string;
  files?: Array<{
    id: string;
    filename: string;
    content_type: string;
  }>;
}

export interface ModelParams {
  max_iterations?: number;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
  tool_servers?: any;
  model_params?: ModelParams;
}

export interface ChatConfig {
  model: string;
  system_prompt?: string;
  tool_servers?: string[];
  model_params?: ModelParams;
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
  choices: Array<{
    message: {
      role: string;
      content: string;
      reasoning_content?: string;
    };
  }>;
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

export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  private: boolean;
  html_url: string;
  updated_at: string;
}

export interface FileNode {
  path: string;
  name: string;
  type: 'file' | 'dir';
  size?: number;
  children?: FileNode[];
}

export interface TokenEstimate {
  total_tokens: number;
  files: Record<string, number>;
}

export interface DefaultChatConfig {
  model?: string | null;
  system_prompt?: string | null;
  tool_servers: string[];
  model_params?: ModelParams | null;
}

export interface Skill {
  name: string;
  path: string;
  exists: boolean;
}

export interface PendingToolApproval {
  id: string;
  tool_name: string;
  arguments: Record<string, any>;
  created_at: string;
}

export interface ApprovalResponse {
  status: string;
  pending_count?: number;
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

  async branchChat(
    chatId: string,
    messageId: string,
    title?: string
  ): Promise<ChatWithMessages> {
    return this.request(`/chats/${chatId}/branch`, {
      method: 'POST',
      body: JSON.stringify({ message_id: messageId, title }),
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

  async retryLastMessage(
    chatId: string
  ): Promise<SendMessageResponse> {
    return this.request(`/chats/${chatId}/retry`, {
      method: 'POST',
    });
  }

  async editLastMessage(
    chatId: string,
    message: string
  ): Promise<SendMessageResponse> {
    return this.request(`/chats/${chatId}/edit`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  // Configuration endpoints
  async listModels(): Promise<{ object: string; data: Model[] }> {
    return this.request('/config/models');
  }

  async getDefaultChatConfig(): Promise<DefaultChatConfig> {
    return this.request('/config/default-chat');
  }

  async listChatbots(): Promise<{ chatbots: Array<{
    name: string;
    system_prompt: string;
    provider: string;
    model_id: string;
    tool_servers: string[];
    temperature?: number;
    max_tokens?: number;
    max_iterations: number;
  }> }> {
    return this.request('/config/chatbots');
  }

  async listProviders(): Promise<{ providers: Array<{
    name: string;
    api_base: string;
    models: string[];
  }> }> {
    return this.request('/config/providers');
  }

  // Tools endpoints
  async listTools(): Promise<{ tool_servers: ToolServer[] }> {
    return this.request('/tools');
  }

  // Skills endpoints
  async listSkills(): Promise<{ skills: Skill[] }> {
    return this.request('/skills');
  }

  async uploadFiles(chatId: string, files: File[]): Promise<{ filenames: string[] }> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const url = `${this.baseURL}/chats/${chatId}/files`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary for multipart/form-data
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async removeUploadedFile(chatId: string, filename: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/chats/${chatId}/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
  }

  // GitHub endpoints
  async listGitHubRepositories(): Promise<{ repositories: GitHubRepository[] }> {
    return this.request('/github/repositories');
  }

  async browseGitHubTree(repo: string, path: string = ""): Promise<FileNode> {
    return this.request(`/github/tree?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(path)}`);
  }

  async estimateGitHubTokens(repo: string, paths: string[], excludePaths?: string[]): Promise<TokenEstimate> {
    return this.request('/github/estimate', {
      method: 'POST',
      body: JSON.stringify({ repo, paths, exclude_paths: excludePaths || [] }),
    });
  }

  async addGitHubFilesToChat(chatId: string, repo: string, paths: string[], excludePaths?: string[]): Promise<{ success: boolean; files_added: string[]; count: number }> {
    return this.request(`/chats/${chatId}/github/files`, {
      method: 'POST',
      body: JSON.stringify({ repo, paths, exclude_paths: excludePaths || [] }),
    });
  }

  async removeGitHubFilesFromChat(chatId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/chats/${chatId}/github/files`, {
      method: 'DELETE',
    });
  }

  // Media endpoints
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'audio.webm');

    const url = `${this.baseURL}/media/transcribe`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary for multipart/form-data
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Tool Approval endpoints
  async getPendingApprovals(chatId: string): Promise<{ approvals: PendingToolApproval[] }> {
    return this.request(`/chats/${chatId}/approvals`);
  }

  async approveTool(chatId: string, approvalId: string): Promise<ApprovalResponse> {
    return this.request(`/chats/${chatId}/approvals/${approvalId}/approve`, {
      method: 'POST',
    });
  }

  async denyTool(chatId: string, approvalId: string): Promise<ApprovalResponse> {
    return this.request(`/chats/${chatId}/approvals/${approvalId}/deny`, {
      method: 'POST',
    });
  }
}

export const api = new ApiClient();
