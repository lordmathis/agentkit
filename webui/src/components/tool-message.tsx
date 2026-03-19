import { Wrench } from "lucide-react";
import { cn } from "../lib/utils";
import { useState } from "react";
import type { Message } from "../lib/api";

interface ToolMessageProps {
  message: Message;
}

export function ToolMessage({ message }: ToolMessageProps) {
  const [showToolResult, setShowToolResult] = useState(false);

  return (
    <div
      className="group relative flex gap-4 px-4 py-3 sm:px-6 border rounded-md bg-muted/30"
      style={{
        borderColor: "var(--color-yellow)",
        boxShadow: `0 0 10px color-mix(in oklch, var(--color-yellow) 35%, transparent)`
      }}
    >
      <div className="flex-shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-foreground">
          <Wrench className="h-4 w-4" />
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold leading-none">Tool</p>
        </div>
        
        <button
          onClick={() => setShowToolResult(!showToolResult)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Wrench className="h-3.5 w-3.5" />
          <span>{showToolResult ? "Hide" : "Show"} result</span>
          <svg
            className={cn(
              "h-3 w-3 transition-transform",
              showToolResult && "rotate-180"
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
        
        {showToolResult && (
          <div className="text-foreground">
            <pre className="text-xs whitespace-pre-wrap overflow-auto max-h-60 bg-muted/50 rounded p-3">
              {message.content}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}