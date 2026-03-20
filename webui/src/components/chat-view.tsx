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
import type { ConnectorEntry } from "../lib/api";

export function ChatView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isConnectorDialogOpen, setIsConnectorDialogOpen] = useState(false);
  const [editingConnectorEntry, setEditingConnectorEntry] = useState<ConnectorEntry | null>(null);
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
    getFiles: () => files.getAllFiles(),
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
          connectorEntries={files.connectorEntries}
          onRemoveFile={files.removeFile}
          onRemoveConnectorEntry={files.removeConnectorEntry}
          onEditConnectorEntry={(connectorId, resourceId) => {
            const entry = files.connectorEntries.find(
              e => e.connectorId === connectorId && e.resourceId === resourceId
            );
            if (entry) {
              setEditingConnectorEntry(entry);
              setIsConnectorDialogOpen(true);
            }
          }}
          onFileUploadClick={handleFileUploadClick}
          onConnectorDialogOpen={() => {
            setEditingConnectorEntry(null);
            setIsConnectorDialogOpen(true);
          }}
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
        onOpenChange={(open) => {
          setIsConnectorDialogOpen(open);
          if (!open) setEditingConnectorEntry(null);
        }}
        chatId={currentConversationId}
        editingEntry={editingConnectorEntry ?? undefined}
        onFilesAdded={(entry) => {
          if (editingConnectorEntry) {
            files.updateConnectorEntry(
              editingConnectorEntry.connectorId,
              editingConnectorEntry.resourceId,
              entry
            );
          } else {
            files.addConnectorEntry(entry);
          }
          setEditingConnectorEntry(null);
        }}
      />
    </div>
  );
}
