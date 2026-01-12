import { PanelLeftClose, MessageSquare, Plus } from "lucide-react";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

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
}

export function Sidebar({
  isOpen,
  onToggle,
  conversations,
  currentConversationId,
  onConversationSelect,
  onNewConversation,
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
      >
        <div className={`flex h-full flex-col ${isOpen ? "" : "lg:hidden"}`}>
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold text-foreground">
              Conversations
            </h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="h-8 w-8"
            >
              <PanelLeftClose className="h-5 w-5" />
              <span className="sr-only">Close sidebar</span>
            </Button>
          </div>

          {/* New conversation button */}
          <div className="shrink-0 px-3 py-3">
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={onNewConversation}
            >
              <Plus className="h-4 w-4" />
              New Conversation
            </Button>
          </div>

          {/* Conversations list */}
          <ScrollArea className="flex-1">
            <div className="space-y-1 px-3 pb-4">
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => onConversationSelect?.(conversation.id)}
                  className={`
                    group w-full rounded-lg px-3 py-2.5 text-left transition-colors
                    ${
                      currentConversationId === conversation.id
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted text-foreground"
                    }
                  `}
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        currentConversationId === conversation.id
                          ? "text-primary"
                          : "text-muted-foreground"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">
                        {conversation.title}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {conversation.timestamp}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </>
  );
}
