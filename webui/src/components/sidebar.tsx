import { PanelLeftClose, MessageSquare, Plus, Trash2 } from "lucide-react";
import { Button } from "./ui/button";

export interface Conversation {
  id: string;
  title: string;
  timestamp: string;
  preview?: string;
}

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  currentConversationId?: string;
  onConversationSelect?: (conversationId: string) => void;
  onNewConversation?: () => void;
  onDeleteConversation?: (conversationId: string) => void;
  isLoading?: boolean;
}

export function Sidebar({
  isOpen,
  onToggle,
  conversations,
  currentConversationId,
  onConversationSelect,
  onNewConversation,
  onDeleteConversation,
  isLoading = false,
}: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed left-0 top-0 z-40 h-screen w-[280px] transform border-r border-border bg-muted/30 backdrop-blur-sm transition-transform duration-200 ease-in-out
          lg:relative lg:z-0
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0 lg:w-0 lg:border-0"}
        `}
        style={{ maxWidth: '280px', overflow: 'hidden' }}
      >
        <div className={`flex h-full flex-col overflow-hidden ${isOpen ? "" : "lg:hidden"}`} style={{ maxWidth: '280px' }}>
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3 overflow-hidden" style={{ maxWidth: '280px' }}>
            <h2 className="text-sm font-semibold text-foreground truncate">
              Conversations
            </h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="h-8 w-8 shrink-0"
            >
              <PanelLeftClose className="h-5 w-5" />
              <span className="sr-only">Close sidebar</span>
            </Button>
          </div>

          {/* New conversation button */}
          <div className="shrink-0 px-3 py-3 overflow-hidden">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 truncate"
              onClick={onNewConversation}
            >
              <Plus className="h-4 w-4 shrink-0" />
              <span className="truncate">New Conversation</span>
            </Button>
          </div>

          {/* Conversations list */}
          <div className="flex-1 overflow-y-auto overflow-x-hidden">
            <div className="space-y-1 px-3 pb-4">
              {isLoading ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  Loading conversations...
                </div>
              ) : conversations.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No conversations yet
                </div>
              ) : (
                conversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`
                      group rounded-lg transition-colors flex items-center pr-2
                      ${
                        currentConversationId === conversation.id
                          ? "bg-primary/10"
                          : "hover:bg-muted"
                      }
                    `}
                  >
                    <button
                      onClick={() => onConversationSelect?.(conversation.id)}
                      className="flex items-start gap-2 flex-1 min-w-0 px-3 py-2.5 text-left"
                    >
                      <MessageSquare
                        className={`mt-0.5 h-4 w-4 shrink-0 ${
                          currentConversationId === conversation.id
                            ? "text-primary"
                            : "text-muted-foreground"
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className={`truncate text-sm font-medium ${
                          currentConversationId === conversation.id
                            ? "text-primary"
                            : "text-foreground"
                        }`}>
                          {conversation.title}
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground truncate">
                          {conversation.timestamp}
                        </div>
                      </div>
                    </button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm(`Delete "${conversation.title}"?`)) {
                          onDeleteConversation?.(conversation.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      <span className="sr-only">Delete conversation</span>
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
