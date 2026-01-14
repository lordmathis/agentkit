import { Send, Bot, Zap, Plus, Upload, X, File } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { ChatMessage, type Message } from "./chat-message";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Sidebar, type Conversation } from "./sidebar";
import {
  ChatSettingsDialog,
  type ChatSettings,
} from "./chat-settings-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { api } from "../lib/api";

// Helper function to format model ID as a display label
const getModelLabel = (modelValue: string): string => {
  // Remove provider prefix if present (e.g., "openai:gpt-4" -> "gpt-4")
  const modelId = modelValue.includes(':') ? modelValue.split(':')[1] : modelValue;
  
  // Convert snake_case or kebab-case to Title Case
  return modelId
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Helper function to format tool server name as a display label
const getToolLabel = (toolId: string): string => {
  // Convert snake_case or kebab-case to Title Case
  return toolId
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Format timestamp for display (e.g., "2 hours ago", "Yesterday")
const formatTimestamp = (isoString: string): string => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? "s" : ""} ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? "s" : ""} ago`;
  return `${Math.floor(diffDays / 365)} year${Math.floor(diffDays / 365) > 1 ? "s" : ""} ago`;
};

export function ChatView() {
  const [inputValue, setInputValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(undefined);
  const [chatSettings, setChatSettings] = useState<ChatSettings>({
    baseModel: "",
    systemPrompt: "",
    enabledTools: [],
  });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle file upload button click
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Handle file selection
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
      
      // Upload files to backend
      const response = await api.uploadFiles(currentConversationId, fileArray);
      
      // Add uploaded files to state
      setUploadedFiles((prev) => [...prev, ...response.filenames]);
      
      // Show success message
      const fileNames = response.filenames.join(", ");
      console.log(`Successfully uploaded: ${fileNames}`);
      
      // Clear the file input
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
  const handleRemoveFile = (filename: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f !== filename));
  };

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

  // Load default model on first mount
  useEffect(() => {
    const loadDefaultModel = async () => {
      if (chatSettings.baseModel) {
        // Already has a model, skip
        return;
      }

      try {
        const response = await api.listModels();
        if (response.data && response.data.length > 0) {
          // Set the first available model as default
          setChatSettings((prev) => ({
            ...prev,
            baseModel: response.data[0].id,
          }));
        }
      } catch (error) {
        console.error("Failed to load default model:", error);
      }
    };

    loadDefaultModel();
  }, [chatSettings.baseModel]);

  // Fetch chats from the backend
  useEffect(() => {
    const fetchChats = async () => {
      try {
        setIsLoadingChats(true);
        const response = await api.listChats(20);
        
        // Convert backend chat format to frontend Conversation format
        const formattedChats: Conversation[] = response.chats.map((chat) => ({
          id: chat.id,
          title: chat.title,
          timestamp: formatTimestamp(chat.updated_at),
          preview: chat.model || undefined,
        }));
        
        setConversations(formattedChats);
      } catch (error) {
        console.error("Failed to fetch chats:", error);
        // Keep empty array on error
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
        
        // Convert backend messages to frontend format
        const formattedMessages: Message[] = chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          reasoning_content: msg.reasoning_content,
          files: msg.files,
        }));
        
        setMessages(formattedMessages);
        
        // Update chat settings from the loaded chat data
        setChatSettings({
          baseModel: chatData.model || "",
          systemPrompt: chatData.system_prompt || "",
          enabledTools: chatData.tool_servers || [],
        });
        
        // Clear uploaded files when switching conversations
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

  // Handle creating a new conversation
  const handleNewConversation = async () => {
    try {
      // Validate that required settings are present
      if (!chatSettings.baseModel) {
        alert("Please select a base model in the settings before creating a new conversation.");
        return;
      }

      // Create the chat with current settings
      const newChat = await api.createChat({
        title: "Untitled Chat",
        config: {
          model: chatSettings.baseModel,
          system_prompt: chatSettings.systemPrompt || undefined,
          tool_servers: chatSettings.enabledTools.length > 0 ? chatSettings.enabledTools : undefined,
        },
      });

      // Add the new chat to the conversations list
      const newConversation: Conversation = {
        id: newChat.id,
        title: newChat.title,
        timestamp: formatTimestamp(newChat.created_at),
        preview: newChat.model || undefined,
      };
      setConversations((prev) => [newConversation, ...prev]);

      // Switch to the new conversation
      setCurrentConversationId(newChat.id);
      
      // Clear messages for the new conversation
      setMessages([]);
    } catch (error) {
      console.error("Failed to create new conversation:", error);
      alert(`Failed to create new conversation: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  // Handle deleting a conversation
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await api.deleteChat(conversationId);
      
      // Remove from conversations list
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      
      // If we deleted the current conversation, clear it
      if (currentConversationId === conversationId) {
        setCurrentConversationId(undefined);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
      alert(`Failed to delete conversation: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  };

  // Handle sending a message
  const handleSendMessage = async () => {
    const trimmedMessage = inputValue.trim();
    
    // Validate input
    if (!trimmedMessage) {
      return;
    }

    // Must have a current conversation to send messages
    if (!currentConversationId) {
      alert("Please create or select a conversation first");
      return;
    }

    try {
      setIsSending(true);
      
      // Clear input and uploaded files immediately for better UX
      setInputValue("");
      setUploadedFiles([]);

      // Add user message to UI optimistically
      const tempUserMessage: Message = {
        id: `temp-user-${Date.now()}`,
        role: "user",
        content: trimmedMessage,
      };
      setMessages((prev) => [...prev, tempUserMessage]);

      // Send message to backend
      const response = await api.sendMessage(currentConversationId, {
        message: trimmedMessage,
        stream: false,
      });

      // Extract assistant message from OpenAI-style response
      const assistantContent = response.choices?.[0]?.message?.content || "No response";

      // Replace temp user message and add assistant response
      setMessages((prev) => {
        // Remove temp message
        const withoutTemp = prev.filter((m) => m.id !== tempUserMessage.id);
        
        // Add both user and assistant messages
        // These are temporary - we'll reload from backend to get proper IDs
        return [
          ...withoutTemp,
          {
            id: `user-${Date.now()}`,
            role: "user" as const,
            content: trimmedMessage,
          },
          {
            id: `assistant-${Date.now()}`,
            role: "assistant" as const,
            content: assistantContent,
          },
        ];
      });

      // Reload messages from backend to get proper message IDs
      // Do this in the background without blocking the UI
      try {
        const chatData = await api.getChat(currentConversationId);
        const formattedMessages: Message[] = chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          reasoning_content: msg.reasoning_content,
          files: msg.files,
        }));
        setMessages(formattedMessages);
      } catch (error) {
        console.error("Failed to reload messages:", error);
        // Keep the temporary messages if reload fails
      }


      // Refresh conversations to update the timestamp and preview
      await refreshConversations();
    } catch (error) {
      console.error("Failed to send message:", error);
      alert(`Failed to send message: ${error instanceof Error ? error.message : "Unknown error"}`);
      
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("temp-user-")));
      
      // Restore input value so user can try again
      setInputValue(trimmedMessage);
    } finally {
      setIsSending(false);
    }
  };

  // Handle keyboard shortcuts in textarea
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without shift sends the message
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="relative flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onConversationSelect={setCurrentConversationId}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isLoading={isLoadingChats}
      />

      {/* Main chat area */}
      <div className="relative flex flex-1 flex-col">
        {/* Header - Sticky at top */}
        <div className="sticky top-0 z-20 shrink-0 border-b border-border bg-muted/30 backdrop-blur-sm px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(true)}
                className="h-8 w-8 shrink-0"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect width="18" height="18" x="3" y="3" rx="2" />
                  <path d="M9 3v18" />
                </svg>
                <span className="sr-only">Open sidebar</span>
              </Button>
            )}
            <h1 className="text-lg font-semibold text-foreground">
              AgentKit Chat
            </h1>
          </div>
        </div>

        {/* Messages Container */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="mx-auto max-w-3xl pb-6">
            {isLoadingMessages ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center text-muted-foreground">
                  Loading messages...
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <p className="text-lg font-medium text-foreground">
                    No messages yet
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {currentConversationId 
                      ? "Start a conversation by typing a message below"
                      : "Select a conversation from the sidebar or create a new one"}
                  </p>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isSending && (
                  <div className="group relative flex gap-4 px-4 py-6 sm:px-6 bg-muted/50">
                    <div className="flex-shrink-0">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-foreground">
                        <Bot className="h-5 w-5" />
                      </div>
                    </div>
                    <div className="flex-1 space-y-2 overflow-hidden">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold leading-none">
                          Assistant
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <div className="flex gap-1">
                          <span className="animate-bounce" style={{ animationDelay: "0ms" }}>●</span>
                          <span className="animate-bounce" style={{ animationDelay: "150ms" }}>●</span>
                          <span className="animate-bounce" style={{ animationDelay: "300ms" }}>●</span>
                        </div>
                        <span>Generating response...</span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input Area - Sticky at bottom */}
        <div className="sticky bottom-0 z-20 shrink-0 border-t border-border bg-background">
          <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1">
                <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{getModelLabel(chatSettings.baseModel)}</span>
              </div>
              {chatSettings.enabledTools.length > 0 && (
                <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1">
                  <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {chatSettings.enabledTools.map((t) => getToolLabel(t)).join(", ")}
                  </span>
                </div>
              )}
            </div>
            {/* Uploaded files display */}
            {uploadedFiles.length > 0 && (
              <div className="mb-3 flex flex-wrap items-center gap-2">
                {uploadedFiles.map((filename, index) => (
                  <div
                    key={`${filename}-${index}`}
                    className="flex items-center gap-1.5 rounded-md border border-border bg-primary/10 px-2 py-1 text-xs"
                  >
                    <File className="h-3.5 w-3.5 text-primary" />
                    <span className="text-primary font-medium">{filename}</span>
                    <button
                      onClick={() => handleRemoveFile(filename)}
                      className="ml-1 hover:text-destructive transition-colors"
                      aria-label={`Remove ${filename}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message here..."
                className="min-h-[60px] resize-none pr-32 overflow-y-auto"
                rows={1}
                disabled={isSending || !currentConversationId}
              />
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="absolute bottom-2 right-2 flex gap-1">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      size="icon" 
                      variant="ghost"
                      className="h-9 w-9" 
                      disabled={isSending || isUploadingFiles || !currentConversationId}
                    >
                      <Plus className="h-5 w-5" />
                      <span className="sr-only">Add attachments</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" side="top">
                    <DropdownMenuItem onClick={handleFileUploadClick} disabled={isUploadingFiles}>
                      <Upload className="mr-2 h-4 w-4" />
                      <span>{isUploadingFiles ? "Uploading..." : "Upload files"}</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <ChatSettingsDialog
                  settings={chatSettings}
                  onSettingsChange={setChatSettings}
                  currentChatId={currentConversationId}
                  onChatUpdated={refreshConversations}
                />
                <Button 
                  size="icon" 
                  className="h-9 w-9" 
                  type="submit"
                  onClick={handleSendMessage}
                  disabled={isSending || !currentConversationId || !inputValue.trim()}
                >
                  <Send className="h-5 w-5" />
                  <span className="sr-only">Send message</span>
                </Button>
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
