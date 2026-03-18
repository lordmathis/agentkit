import { useState, useEffect, useRef } from "react";
import { Sidebar } from "./sidebar";
import { AddConnectorDialog } from "./add-connector-dialog";
import { ChatHeader } from "./chat-header";
import { MessagesList } from "./messages-list";
import { ChatInput } from "./chat-input";
import { useConversations } from "../hooks/use-conversations";
import { useMessages } from "../hooks/use-messages";
import { useChatFiles } from "../hooks/use-chat-files";

export function ChatView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isConnectorDialogOpen, setIsConnectorDialogOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>();
  const [inputValue, setInputValue] = useState("");
  const [isEditingMode, setIsEditingMode] = useState(false);

  const conversations = useConversations();
  const messages = useMessages(currentConversationId);
  const files = useChatFiles(currentConversationId);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle file upload button click
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Handle connector dialog open
  const handleConnectorDialogOpen = () => {
    setIsConnectorDialogOpen(true);
  };

  // Get current conversation title
  const currentConversation = conversations.conversations.find(
    (conv) => conv.id === currentConversationId
  );
  const currentChatTitle = currentConversation?.title;

  // Update page title when chat changes
  useEffect(() => {
    if (currentChatTitle) {
      document.title = `${currentChatTitle} - AgentKit Chat`;
    } else {
      document.title = "AgentKit Chat";
    }
  }, [currentChatTitle]);

  const handleSend = async () => {
    if (!inputValue.trim() || messages.isSending) return;
    
    const text = inputValue.trim();
    const fileIds = files.uploadedFiles.map(f => f.id);
    
    setInputValue("");
    files.clearAll();
    
    if (isEditingMode) {
      await messages.edit(text);
      setIsEditingMode(false);
    } else {
      await messages.send(text, fileIds);
    }
    conversations.refresh();
  };

  const handleRetry = async () => {
    await messages.retry();
    conversations.refresh();
  };

  const handleEdit = () => {
    const lastUserMessage = [...messages.messages]
      .reverse()
      .find((msg) => msg.role === "user");

    if (!lastUserMessage) return;

    setInputValue(lastUserMessage.content);
    setIsEditingMode(true);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex h-screen bg-background">
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        conversations={conversations.conversations}
        currentConversationId={currentConversationId}
        onConversationSelect={setCurrentConversationId}
        onNewConversation={async () => {
          const id = await conversations.createConversation();
          setCurrentConversationId(id);
        }}
        onDeleteConversation={async (id) => {
          await conversations.deleteConversation(id);
          if (currentConversationId === id) setCurrentConversationId(undefined);
        }}
        isLoading={conversations.isLoading}
      />

      <div className="relative flex flex-1 flex-col">
        <ChatHeader 
          sidebarOpen={sidebarOpen} 
          onToggleSidebar={() => setSidebarOpen(true)}
          chatTitle={currentChatTitle}
        />

        <MessagesList
          messages={messages.messages}
          isLoading={messages.isLoading}
          isSending={messages.isSending}
          currentConversationId={currentConversationId}
          messagesEndRef={messagesEndRef}
          onBranch={async (messageId) => {
            const id = await conversations.branchConversation(currentConversationId!, messageId);
            setCurrentConversationId(id);
          }}
          onRetry={handleRetry}
          onEdit={handleEdit}
        />

        <ChatInput
          inputValue={inputValue}
          isEditingMode={isEditingMode}
          onInputChange={setInputValue}
          onSend={handleSend}
          onKeyDown={handleKeyDown}
          isSending={messages.isSending}
          isUploadingFiles={files.isUploading}
          currentConversationId={currentConversationId}
          chatSettings={messages.chatSettings}
          onSettingsChange={messages.setChatSettings}
          uploadedFiles={files.uploadedFiles}
          connectorFiles={files.connectorFiles}
          onRemoveFile={files.removeFile}
          onRemoveConnectorFiles={files.removeConnectorFiles}
          onFileUploadClick={handleFileUploadClick}
          onConnectorDialogOpen={handleConnectorDialogOpen}
          onChatUpdated={conversations.refresh}
          textareaRef={textareaRef}
          fileInputRef={fileInputRef}
          onFileChange={(e) => {
            if (e.target.files) files.uploadFiles(Array.from(e.target.files));
          }}
        />
      </div>

      <AddConnectorDialog
        open={isConnectorDialogOpen}
        onOpenChange={setIsConnectorDialogOpen}
        chatId={currentConversationId}
        onFilesAdded={(connectorId, resourceId, paths, excludePaths, uploaded) => {
          files.setConnectorFiles(connectorId, resourceId, paths, excludePaths, uploaded);
        }}
        initialConnector={files.connectorFiles.connectorId}
        initialRepo={files.connectorFiles.resourceId}
        initialPaths={files.connectorFiles.paths}
        initialExcludePaths={files.connectorFiles.excludePaths}
      />
    </div>
  );
}
