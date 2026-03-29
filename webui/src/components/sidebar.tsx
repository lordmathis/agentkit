import { PanelLeftClose, MessageSquare, Plus, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

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
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onToggle}
        />
      )}

      <div
        className={`
          fixed left-0 top-0 z-40 h-screen w-[280px] transform border-r-2 bg-[#10100e]/90 backdrop-blur-sm transition-transform duration-200 ease-in-out
          lg:relative lg:z-0
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0 lg:w-0 lg:border-0"}
        `}
        style={{ maxWidth: '280px', overflow: 'hidden', borderRightColor: 'rgba(245, 216, 0, 0.2)' }}
      >
        <div className={`flex h-full flex-col overflow-hidden ${isOpen ? "" : "lg:hidden"}`} style={{ maxWidth: '280px' }}>
          <div
            className="flex shrink-0 items-center justify-between border-b px-4 py-3 overflow-hidden"
            style={{ maxWidth: '280px', borderColor: 'rgba(245, 216, 0, 0.15)' }}
          >
            <h2 className="font-bold text-primary truncate uppercase tracking-[0.18em]"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '14px' }}>
              Sessions
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

          <div className="shrink-0 px-3 py-3 overflow-hidden">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 truncate text-xs uppercase tracking-wider"
              onClick={onNewConversation}
            >
              <Plus className="h-4 w-4 shrink-0" />
              <span className="truncate">New Session</span>
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto overflow-x-hidden">
            <TooltipProvider delayDuration={300}>
              <div className="space-y-1.5 px-3 pb-4">
                {isLoading ? (
                  <div className="py-8 text-center text-xs text-muted-foreground uppercase tracking-widest">
                    Loading...
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="py-8 text-center text-xs text-muted-foreground uppercase tracking-widest">
                    No sessions
                  </div>
                ) : (
                  conversations.map((conversation) => (
                    <Tooltip key={conversation.id}>
                      <TooltipTrigger asChild>
                        <div
                          className={`
                            group relative transition-all duration-150 flex items-center pr-2 cursor-pointer overflow-hidden
                            ${
                              currentConversationId === conversation.id
                                ? "border border-[rgba(245,216,0,0.3)] bg-[rgba(245,216,0,0.06)]"
                                : "border border-[rgba(245,216,0,0.1)] bg-[#18180f] hover:border-[rgba(245,216,0,0.25)]"
                            }
                          `}
                          style={{
                            clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)",
                          }}
                          onClick={() => onConversationSelect?.(conversation.id)}
                        >
                          {currentConversationId === conversation.id && (
                            <div
                              className="absolute top-0 right-0 w-[10px] h-[10px] opacity-40"
                              style={{
                                background: '#f5d800',
                                clipPath: 'polygon(0 0, 100% 100%, 100% 0)',
                              }}
                            />
                          )}
                          <div className="flex items-start gap-2 flex-1 min-w-0 px-3 py-2.5 text-left">
                            <MessageSquare
                              className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                                currentConversationId === conversation.id
                                  ? "text-primary"
                                  : "text-muted-foreground"
                              }`}
                            />
                            <div className="min-w-0 flex-1">
                              <div
                                className="cp-label text-primary mb-1"
                                style={{ color: currentConversationId === conversation.id ? '#f5d800' : '#a89e88' }}
                              >
                                LOG #{conversation.id.slice(0, 4).toUpperCase()} //
                              </div>
                              <div className={`truncate text-sm ${
                                currentConversationId === conversation.id
                                  ? "text-foreground"
                                  : "text-[#e8e0c8]/70"
                              }`}
                              style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.03em' }}
                              >
                                {conversation.title}
                              </div>
                              <div className="cp-label mt-1" style={{ color: '#a89e88' }}>
                                {conversation.timestamp}
                              </div>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="group/delete h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-transparent"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm(`Delete "${conversation.title}"?`)) {
                                onDeleteConversation?.(conversation.id);
                              }
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5 text-muted-foreground group-hover/delete:text-[var(--color-cp-red)]" />
                            <span className="sr-only">Delete</span>
                          </Button>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-xs">
                        <p className="font-medium">{conversation.title}</p>
                      </TooltipContent>
                    </Tooltip>
                  ))
                )}
              </div>
            </TooltipProvider>
          </div>
        </div>
      </div>
    </>
  );
}
