import { useState, useEffect, useRef } from "react";
import { Sidebar } from "./sidebar";
import { AddConnectorDialog } from "./add-connector-dialog";
import { ChatHeader } from "./chat-header";
import { MessagesList } from "./messages-list";
import { ChatInput } from "./chat-input";
import { useConversations } from "../hooks/use-conversations";
import { useMessages } from "../hooks/use-messages";
import { useChatFiles } from "../hooks/use-chat-files";
import { useChatInput } from "../hooks/use-chat-input";

export function ChatView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isConnectorDialogOpen, setIsConnectorDialogOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>();

  const conversations = useConversations();
  const messages = useMessages(currentConversationId);
  const files = useChatFiles(currentConversationId);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const chatInput = useChatInput({
    onSend: messages.send,
    onEdit: messages.edit,
    messages: messages.messages,
    getFileIds: () => files.uploadedFiles.map(f => f.id),
    isSending: messages.isSending,
    onSendComplete: () => {
      files.clearAll();
      conversations.refresh();
    },
    onEditComplete: () => {
      conversations.refresh();
    },
  });

  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleConnectorDialogOpen = () => {
    setIsConnectorDialogOpen(true);
  };

  const currentConversation = conversations.conversations.find(
    (conv) => conv.id === currentConversationId
  );
  const currentChatTitle = currentConversation?.title;

  useEffect(() => {
    if (currentChatTitle) {
      document.title = `${currentChatTitle} - AgentKit Chat`;
    } else {
      document.title = "AgentKit Chat";
    }
  }, [currentChatTitle]);

  const handleRetry = async () => {
    await messages.retry();
    conversations.refresh();
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
          onEdit={chatInput.handleEdit}
        />

        <ChatInput
          inputValue={chatInput.inputValue}
          isEditingMode={chatInput.isEditingMode}
          onInputChange={chatInput.setInputValue}
          onCancelEdit={chatInput.cancelEdit}
          onSend={chatInput.handleSend}
          onKeyDown={chatInput.handleKeyDown}
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
          textareaRef={chatInput.textareaRef}
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
        initialInstance={files.connectorFiles.connectorId}
        initialConnector={files.connectorFiles.resourceId}
        initialPaths={files.connectorFiles.paths}
        initialExcludePaths={files.connectorFiles.excludePaths}
      />
    </div>
  );
}
