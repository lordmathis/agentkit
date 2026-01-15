import { Button } from "./ui/button";

interface ChatHeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export function ChatHeader({ sidebarOpen, onToggleSidebar }: ChatHeaderProps) {
  return (
    <div className="sticky top-0 z-20 shrink-0 border-b border-border bg-muted/30 backdrop-blur-sm px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3">
        {!sidebarOpen && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
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
  );
}
