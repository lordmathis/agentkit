import { useState, useEffect } from "react";
import { Sidebar } from "./sidebar";
import { AddConnectorDialog } from "./add-connector-dialog";
import { ChatHeader } from "./chat-header";
import { MessagesList } from "./messages-list";
import { ChatInput } from "./chat-input";
import { useChatManager } from "../hooks/use-chat-manager";


export function ChatView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isConnectorDialogOpen, setIsConnectorDialogOpen] = useState(false);

  const {
    inputValue,
    isEditingMode,
    currentConversationId,
    chatSettings,
    conversations,
    isLoadingChats,
    messages,
    isLoadingMessages,
    isSending,
    isUploadingFiles,
    uploadedFiles,
    connectorFiles,
    textareaRef,
    messagesEndRef,
    fileInputRef,
    setInputValue,
    setCurrentConversationId,
    setChatSettings,
    handleFileChange,
    handleRemoveFile,
    handleRemoveConnectorFiles,
    handleFilesAddedFromConnector,
    handleNewConversation,
    handleDeleteConversation,
    handleBranchChat,
    handleSendMessage,
    handleRetryMessage,
    handleEditMessage,
    handleKeyDown,
    refreshConversations,
  } = useChatManager();

  // Handle file upload button click
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Handle connector dialog open
  const handleConnectorDialogOpen = () => {
    setIsConnectorDialogOpen(true);
  };

  // Get current conversation title
  const currentConversation = conversations.find(
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
        {/* Header */}
        <ChatHeader 
          sidebarOpen={sidebarOpen} 
          onToggleSidebar={() => setSidebarOpen(true)}
          chatTitle={currentChatTitle}
        />

        {/* Messages Container */}
        <MessagesList
          messages={messages}
          isLoading={isLoadingMessages}
          isSending={isSending}
          currentConversationId={currentConversationId}
          messagesEndRef={messagesEndRef}
          onBranch={handleBranchChat}
          onRetry={handleRetryMessage}
          onEdit={handleEditMessage}
        />

        {/* Input Area */}
        <ChatInput
          inputValue={inputValue}
          isEditingMode={isEditingMode}
          onInputChange={setInputValue}
          onSend={handleSendMessage}
          onKeyDown={handleKeyDown}
          isSending={isSending}
          isUploadingFiles={isUploadingFiles}
          currentConversationId={currentConversationId}
          chatSettings={chatSettings}
          onSettingsChange={setChatSettings}
          uploadedFiles={uploadedFiles}
          connectorFiles={connectorFiles}
          onRemoveFile={handleRemoveFile}
          onRemoveConnectorFiles={handleRemoveConnectorFiles}
          onFileUploadClick={handleFileUploadClick}
          onConnectorDialogOpen={handleConnectorDialogOpen}
          onChatUpdated={refreshConversations}
          textareaRef={textareaRef}
          fileInputRef={fileInputRef}
          onFileChange={handleFileChange}
        />
      </div>

      {/* Connector Dialog */}
      <AddConnectorDialog
        open={isConnectorDialogOpen}
        onOpenChange={setIsConnectorDialogOpen}
        chatId={currentConversationId}
        onFilesAdded={handleFilesAddedFromConnector}
        initialRepo={connectorFiles.repo}
        initialPaths={connectorFiles.paths}
        initialExcludePaths={connectorFiles.excludePaths}
      />
    </div>
  );
}