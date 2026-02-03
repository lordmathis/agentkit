import { useState, useEffect } from "react";
import { Sidebar } from "./sidebar";
import { AddGitHubDialog } from "./add-github-dialog";
import { ChatHeader } from "./chat-header";
import { MessagesList } from "./messages-list";
import { ChatInput } from "./chat-input";
import { useChatManager } from "../hooks/use-chat-manager";


export function ChatView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isGitHubDialogOpen, setIsGitHubDialogOpen] = useState(false);

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
    githubFiles,
    textareaRef,
    messagesEndRef,
    fileInputRef,
    setInputValue,
    setCurrentConversationId,
    setChatSettings,
    handleFileChange,
    handleRemoveFile,
    handleRemoveGitHubFiles,
    handleFilesAddedFromGitHub,
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

  // Handle GitHub dialog open
  const handleGitHubDialogOpen = () => {
    setIsGitHubDialogOpen(true);
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
          githubFiles={githubFiles}
          onRemoveFile={handleRemoveFile}
          onRemoveGitHubFiles={handleRemoveGitHubFiles}
          onFileUploadClick={handleFileUploadClick}
          onGitHubDialogOpen={handleGitHubDialogOpen}
          onChatUpdated={refreshConversations}
          textareaRef={textareaRef}
          fileInputRef={fileInputRef}
          onFileChange={handleFileChange}
        />
      </div>

      {/* GitHub Dialog */}
      <AddGitHubDialog
        open={isGitHubDialogOpen}
        onOpenChange={setIsGitHubDialogOpen}
        chatId={currentConversationId}
        onFilesAdded={handleFilesAddedFromGitHub}
        initialRepo={githubFiles.repo}
        initialPaths={githubFiles.paths}
        initialExcludePaths={githubFiles.excludePaths}
      />
    </div>
  );
}

