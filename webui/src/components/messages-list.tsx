import { Bot } from "lucide-react";
import { ChatMessage } from "./chat-message";
import { ScrollArea } from "./ui/scroll-area";
import type { Message } from "../lib/api";

interface MessagesListProps {
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;
  currentConversationId: string | undefined;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  onBranch?: (messageId: string) => void;
  onRetry?: () => void;
  onEdit?: () => void;
}

export function MessagesList({
  messages,
  isLoading,
  isSending,
  currentConversationId,
  messagesEndRef,
  onBranch,
  onRetry,
  onEdit,
}: MessagesListProps) {
  return (
    <ScrollArea className="flex-1 min-h-0">
      <div className="mx-auto max-w-3xl pb-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center text-muted-foreground">Loading messages...</div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <p className="text-lg font-medium text-foreground">No messages yet</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {currentConversationId
                  ? "Start a conversation by typing a message below"
                  : "Select a conversation from the sidebar or create a new one"}
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => {
              const isLastMessage = index === messages.length - 1;
              const isLastAssistantMessage = isLastMessage && message.role === "assistant";
              
              // Find the last user message in the entire conversation
              const lastUserMessageIndex = [...messages].reverse().findIndex(m => m.role === "user");
              const isLastUserMessage = lastUserMessageIndex !== -1 && index === messages.length - 1 - lastUserMessageIndex;
              
              return (
                <ChatMessage 
                  key={message.id} 
                  message={message} 
                  onBranch={onBranch} 
                  onRetry={isLastAssistantMessage ? onRetry : undefined}
                  onEdit={onEdit}
                  isLastUserMessage={isLastUserMessage}
                />
              );
            })}
            {isSending && (
              <div className="group relative flex gap-4 px-4 py-6 sm:px-6 bg-muted/50">
                <div className="flex-shrink-0">
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-foreground">
                    <Bot className="h-5 w-5" />
                  </div>
                </div>
                <div className="flex-1 space-y-2 overflow-hidden">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold leading-none">Assistant</p>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="flex gap-1">
                      <span className="animate-bounce" style={{ animationDelay: "0ms" }}>
                        ●
                      </span>
                      <span className="animate-bounce" style={{ animationDelay: "150ms" }}>
                        ●
                      </span>
                      <span className="animate-bounce" style={{ animationDelay: "300ms" }}>
                        ●
                      </span>
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
  );
}
