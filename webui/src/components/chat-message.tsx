import { Bot, User } from "lucide-react";
import { cn } from "../lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

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
    </div>
  );
}
