import { useState, useRef, useEffect } from "react";
import { type Message } from "../lib/api";
import { type Conversation } from "../components/sidebar";
import { type ChatSettings } from "../components/chat-settings-dialog";
import { api } from "../lib/api";
import { formatTimestamp } from "../lib/formatters";

export function useChatManager() {
  const [inputValue, setInputValue] = useState("");
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(undefined);
  const [chatSettings, setChatSettings] = useState<ChatSettings>({
    baseModel: "",
    systemPrompt: "",
    enabledTools: [],
    modelParams: {
      max_iterations: 5,
      temperature: undefined,
      max_tokens: undefined,
    },
  });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [githubFiles, setGithubFiles] = useState<{
    repo: string;
    paths: string[];
    excludePaths: string[];
  }>({ repo: "", paths: [], excludePaths: [] });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load default chat config on mount
  useEffect(() => {
    const loadDefaultConfig = async () => {
      try {
        const defaultConfig = await api.getDefaultChatConfig();
        setChatSettings({
          baseModel: defaultConfig.model || "",
          systemPrompt: defaultConfig.system_prompt || "",
          enabledTools: defaultConfig.tool_servers || [],
          modelParams: defaultConfig.model_params || {
            max_iterations: 5,
            temperature: undefined,
            max_tokens: undefined,
          },
        });
      } catch (error) {
        console.error("Failed to load default chat config:", error);
      }
    };

    loadDefaultConfig();
  }, []);

  // Function to refresh conversations list
  const refreshConversations = async () => {
    try {
      const response = await api.listChats(20);
      const formattedChats: Conversation[] = response.chats.map((chat) => ({
        id: chat.id,
        title: chat.title,
        timestamp: formatTimestamp(chat.updated_at),
        preview: chat.model || undefined,
      }));
      setConversations(formattedChats);
    } catch (error) {
      console.error("Failed to refresh conversations:", error);
    }
  };

  // Fetch chats from the backend
  useEffect(() => {
    const fetchChats = async () => {
      try {
        setIsLoadingChats(true);
        const response = await api.listChats(20);

        const formattedChats: Conversation[] = response.chats.map((chat) => ({
          id: chat.id,
          title: chat.title,
          timestamp: formatTimestamp(chat.updated_at),
          preview: chat.model || undefined,
        }));

        setConversations(formattedChats);
      } catch (error) {
        console.error("Failed to fetch chats:", error);
        setConversations([]);
      } finally {
        setIsLoadingChats(false);
      }
    };

    fetchChats();
  }, []);

  // Fetch messages when conversation changes
  useEffect(() => {
    const fetchMessages = async () => {
      if (!currentConversationId) {
        setMessages([]);
        setUploadedFiles([]);
        return;
      }

      try {
        setIsLoadingMessages(true);
        const chatData = await api.getChat(currentConversationId);

        const formattedMessages: Message[] = chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          reasoning_content: msg.reasoning_content,
          tool_calls: msg.tool_calls,
          sequence: msg.sequence,
          created_at: msg.created_at,
          files: msg.files,
        }));

        setMessages(formattedMessages);

        setChatSettings({
          baseModel: chatData.model || "",
          systemPrompt: chatData.system_prompt || "",
          enabledTools: chatData.tool_servers || [],
          modelParams: chatData.model_params || {
            max_iterations: 5,
            temperature: undefined,
            max_tokens: undefined,
          },
        });

        setUploadedFiles([]);
      } catch (error) {
        console.error("Failed to fetch messages:", error);
        setMessages([]);
      } finally {
        setIsLoadingMessages(false);
      }
    };

    fetchMessages();
  }, [currentConversationId]);

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 300);
      textarea.style.height = `${newHeight}px`;
    }
  }, [inputValue]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  // Handle file upload
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      return;
    }

    if (!currentConversationId) {
      alert("Please create or select a conversation first");
      return;
    }

    try {
      setIsUploadingFiles(true);
      const fileArray = Array.from(files);

      const response = await api.uploadFiles(currentConversationId, fileArray);

      setUploadedFiles((prev) => [...prev, ...response.filenames]);

      const fileNames = response.filenames.join(", ");
      console.log(`Successfully uploaded: ${fileNames}`);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error("Failed to upload files:", error);
      alert(`Failed to upload files: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsUploadingFiles(false);
    }
  };

  // Handle removing an uploaded file
  const handleRemoveFile = async (filename: string) => {
    if (!currentConversationId) return;

    try {
      await api.removeUploadedFile(currentConversationId, filename);
      setUploadedFiles((prev) => prev.filter((f) => f !== filename));
    } catch (error) {
      console.error("Failed to remove uploaded file:", error);
      setUploadedFiles((prev) => prev.filter((f) => f !== filename));
    }
  };

  // Handle removing GitHub files
  const handleRemoveGitHubFiles = async () => {
    if (!currentConversationId) return;

    try {
      await api.removeGitHubFilesFromChat(currentConversationId);
      setGithubFiles({ repo: "", paths: [], excludePaths: [] });
    } catch (error) {
      console.error("Failed to remove GitHub files:", error);
      setGithubFiles({ repo: "", paths: [], excludePaths: [] });
    }
  };

  // Handle files added from GitHub
  const handleFilesAddedFromGitHub = (
    repo: string,
    paths: string[],
    excludePaths: string[],
    count: number
  ) => {
    console.log(`Successfully added ${count} file${count !== 1 ? "s" : ""} from GitHub`);
    setGithubFiles({ repo, paths, excludePaths });
  };

  // Handle creating a new conversation
  const handleNewConversation = async () => {
    try {
      // Reload default config to ensure we use defaults for new chat
      let defaultConfig;
      try {
        defaultConfig = await api.getDefaultChatConfig();
      } catch (error) {
        console.error("Failed to load default chat config:", error);
        // Fall back to current settings if we can't load defaults
        defaultConfig = {
          model: chatSettings.baseModel,
          system_prompt: chatSettings.systemPrompt,
          tool_servers: chatSettings.enabledTools,
          model_params: chatSettings.modelParams,
        };
      }

      const baseModel = defaultConfig.model || chatSettings.baseModel;
      const systemPrompt = defaultConfig.system_prompt || "";
      const toolServers = defaultConfig.tool_servers || [];
      const modelParams = defaultConfig.model_params || chatSettings.modelParams;

      if (!baseModel) {
        alert("Please select a base model in the settings before creating a new conversation.");
        return;
      }

      const newChat = await api.createChat({
        title: "Untitled Chat",
        config: {
          model: baseModel,
          system_prompt: systemPrompt || undefined,
          tool_servers: toolServers.length > 0 ? toolServers : undefined,
          model_params: modelParams,
        },
      });

      const newConversation: Conversation = {
        id: newChat.id,
        title: newChat.title,
        timestamp: formatTimestamp(newChat.created_at),
        preview: newChat.model || undefined,
      };
      setConversations((prev) => [newConversation, ...prev]);

      setCurrentConversationId(newChat.id);
      setMessages([]);

      // Update UI settings to reflect the new chat's config
      setChatSettings({
        baseModel,
        systemPrompt,
        enabledTools: toolServers,
        modelParams,
      });
    } catch (error) {
      console.error("Failed to create new conversation:", error);
      alert(
        `Failed to create new conversation: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  // Handle deleting a conversation
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await api.deleteChat(conversationId);

      setConversations((prev) => prev.filter((c) => c.id !== conversationId));

      if (currentConversationId === conversationId) {
        setCurrentConversationId(undefined);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
      alert(
        `Failed to delete conversation: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  // Handle branching a conversation
  const handleBranchChat = async (messageId: string) => {
    if (!currentConversationId) {
      alert("No conversation selected");
      return;
    }

    try {
      // Find the current chat title
      const currentChat = conversations.find((c) => c.id === currentConversationId);
      const branchTitle = currentChat ? `${currentChat.title} (branch)` : undefined;

      // Create the branch
      const branchedChat = await api.branchChat(
        currentConversationId,
        messageId,
        branchTitle
      );

      // Add to conversations list
      const newConversation: Conversation = {
        id: branchedChat.id,
        title: branchedChat.title,
        timestamp: formatTimestamp(branchedChat.created_at),
        preview: branchedChat.model || undefined,
      };
      setConversations((prev) => [newConversation, ...prev]);

      // Switch to the new branched chat
      setCurrentConversationId(branchedChat.id);

      // Messages will be loaded by the useEffect watching currentConversationId
    } catch (error) {
      console.error("Failed to branch conversation:", error);
      alert(
        `Failed to branch conversation: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  // Handle sending a message
  const handleSendMessage = async () => {
    const trimmedMessage = inputValue.trim();

    if (!trimmedMessage) {
      return;
    }

    if (!currentConversationId) {
      alert("Please create or select a conversation first");
      return;
    }

    try {
      setIsSending(true);

      setInputValue("");
      setUploadedFiles([]);
      setGithubFiles({ repo: "", paths: [], excludePaths: [] });

      const tempUserMessage: Message = {
        id: `temp-user-${Date.now()}`,
        role: "user",
        content: trimmedMessage,
        sequence: messages.length,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMessage]);

      const response = await api.sendMessage(currentConversationId, {
        message: trimmedMessage,
        stream: false,
      });

      const assistantContent = response.choices?.[0]?.message?.content || "No response";

      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMessage.id);

        return [
          ...withoutTemp,
          {
            id: `user-${Date.now()}`,
            role: "user" as const,
            content: trimmedMessage,
            sequence: withoutTemp.length,
            created_at: new Date().toISOString(),
          },
          {
            id: `assistant-${Date.now()}`,
            role: "assistant" as const,
            content: assistantContent,
            sequence: withoutTemp.length + 1,
            created_at: new Date().toISOString(),
          },
        ];
      });

      // Reload messages from backend to get proper message IDs
      try {
        const chatData = await api.getChat(currentConversationId);
        const formattedMessages: Message[] = chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          reasoning_content: msg.reasoning_content,
          tool_calls: msg.tool_calls,
          sequence: msg.sequence,
          created_at: msg.created_at,
          files: msg.files,
        }));
        setMessages(formattedMessages);
      } catch (error) {
        console.error("Failed to reload messages:", error);
      }

      await refreshConversations();
    } catch (error) {
      console.error("Failed to send message:", error);
      alert(`Failed to send message: ${error instanceof Error ? error.message : "Unknown error"}`);

      setMessages((prev) => prev.filter((m) => !m.id.startsWith("temp-user-")));
      setInputValue(trimmedMessage);
    } finally {
      setIsSending(false);
    }
  };

  // Handle retrying the last message
  const handleRetryMessage = async () => {
    if (!currentConversationId) {
      alert("No conversation selected");
      return;
    }

    try {
      setIsSending(true);

      await api.retryLastMessage(currentConversationId);

      // Reload messages from backend to get the updated message
      try {
        const chatData = await api.getChat(currentConversationId);
        const formattedMessages: Message[] = chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          reasoning_content: msg.reasoning_content,
          tool_calls: msg.tool_calls,
          sequence: msg.sequence,
          created_at: msg.created_at,
          files: msg.files,
        }));
        setMessages(formattedMessages);
      } catch (error) {
        console.error("Failed to reload messages:", error);
      }

      await refreshConversations();
    } catch (error) {
      console.error("Failed to retry message:", error);
      alert(`Failed to retry message: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsSending(false);
    }
  };

  // Handle keyboard shortcuts in textarea
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return {
    // State
    inputValue,
    currentConversationId,
    chatSettings,
    conversations,
    isLoadingChats,
    messages,
    isLoadingMessages,
    isSending,
    isUploadingFiles,
    uploadedFiles,
    githubFiles,

    // Refs
    textareaRef,
    messagesEndRef,
    fileInputRef,

    // Setters
    setInputValue,
    setCurrentConversationId,
    setChatSettings,

    // Handlers
    handleFileChange,
    handleRemoveFile,
    handleRemoveGitHubFiles,
    handleFilesAddedFromGitHub,
    handleNewConversation,
    handleDeleteConversation,
    handleBranchChat,
    handleSendMessage,
    handleRetryMessage,
    handleKeyDown,
    refreshConversations,
  };
}
