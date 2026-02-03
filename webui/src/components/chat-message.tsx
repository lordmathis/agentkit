import { Bot, User, Brain, File, GitBranch, RotateCw } from "lucide-react";
import { cn } from "../lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { useState } from "react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";
import { type Message } from "../lib/api";

interface ChatMessageProps {
  message: Message;
  onBranch?: (messageId: string) => void;
  onRetry?: () => void;
}

export function ChatMessage({ message, onBranch, onRetry }: ChatMessageProps) {
  const isUser = message.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);

  // Debug logging
  if (!isUser && message.tool_calls) {
    console.log("Tool calls for message:", message.id, message.tool_calls);
  }

  return (
    <div
      className={cn(
        "group relative flex gap-4 px-4 py-6 sm:px-6",
        isUser ? "bg-background" : "bg-muted/50"
      )}
    >
      <div className="flex-shrink-0">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-md",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          )}
        >
          {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold leading-none">
            {isUser ? "You" : "Assistant"}
          </p>
        </div>
        
        {/* File attachments - show for user messages */}
        {isUser && message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {message.files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1 text-xs"
              >
                <File className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{file.filename}</span>
              </div>
            ))}
          </div>
        )}
        
        {/* Reasoning content - show if present and it's an assistant message */}
        {!isUser && message.reasoning_content && (
          <div className="mb-2">
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Brain className="h-3.5 w-3.5" />
              <span>{showReasoning ? "Hide" : "Show"} reasoning</span>
              <svg
                className={cn(
                  "h-3 w-3 transition-transform",
                  showReasoning && "rotate-180"
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
            
            {showReasoning && (
              <div className="mt-2 rounded-md border border-border bg-muted/30 p-3">
                <div className="prose prose-sm prose-invert max-w-none text-muted-foreground [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      code: ({ inline, className, children, ...props }: any) => {
                        return inline ? (
                          <code
                            className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                            {...props}
                          >
                            {children}
                          </code>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                      a: ({ children, href, ...props }: any) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary underline hover:text-primary/80"
                          {...props}
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {message.reasoning_content}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Tool calls - show if present and it's an assistant message */}
        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2">
            <div className="flex items-start gap-2 text-xs text-muted-foreground">
              <span className="font-medium">Tools used:</span>
              <div className="flex flex-wrap gap-1.5">
                {message.tool_calls.map((tool, index) => (
                  <TooltipProvider key={index} delayDuration={300}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/50 px-2 py-0.5 font-mono text-xs hover:bg-muted transition-colors cursor-default">
                          {tool.name.replace(/^\w+__/, '')}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-md">
                        <div className="space-y-1">
                          <p className="font-semibold">{tool.name}</p>
                          {Object.keys(tool.arguments).length > 0 && (
                            <div className="text-xs">
                              <p className="font-medium mb-1">Arguments:</p>
                              <pre className="overflow-auto max-h-40 bg-background/50 rounded p-1">
                                {JSON.stringify(tool.arguments, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ))}
              </div>
            </div>
          </div>
        )}
        
        <div className="prose prose-sm prose-invert max-w-none text-foreground [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              // Customize code block styling
              code: ({ inline, className, children, ...props }: any) => {
                return inline ? (
                  <code
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm"
                    {...props}
                  >
                    {children}
                  </code>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              // Customize link styling
              a: ({ children, href, ...props }: any) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline hover:text-primary/80"
                  {...props}
                >
                  {children}
                </a>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
      
      {/* Action buttons - shown on hover */}
      {(onBranch || (onRetry && !isUser)) && (
        <div className="absolute right-4 top-6 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onRetry && !isUser && (
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={onRetry}
                  >
                    <RotateCw className="h-4 w-4" />
                    <span className="sr-only">Retry this message</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left">
                  <p>Retry this message</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          
          {onBranch && (
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => onBranch(message.id)}
                  >
                    <GitBranch className="h-4 w-4" />
                    <span className="sr-only">Branch conversation from here</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left">
                  <p>Branch conversation from here</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      )}
    </div>
  );
}
