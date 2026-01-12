import { Send, Bot, Zap } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { ChatMessage, type Message } from "./chat-message";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import { Sidebar, type Conversation } from "./sidebar";
import {
  ChatSettingsDialog,
  type ChatSettings,
} from "./chat-settings-dialog";

// Dummy messages for demonstration
const dummyMessages: Message[] = [
  {
    id: "1",
    role: "user",
    content: "Hello! Can you help me understand how React hooks work?",
  },
  {
    id: "2",
    role: "assistant",
    content:
      "Of course! React Hooks are functions that let you use state and other React features in functional components. The most commonly used hooks are:\n\n1. **useState** - Lets you add state to functional components\n2. **useEffect** - Lets you perform side effects in your components\n3. **useContext** - Lets you subscribe to React context\n4. **useRef** - Lets you create a mutable reference that persists across renders\n\nWould you like me to explain any of these in more detail?",
  },
  {
    id: "3",
    role: "user",
    content: "Yes, can you show me an example of useState?",
  },
  {
    id: "4",
    role: "assistant",
    content:
      "Here's a simple example of useState:\n\n```javascript\nimport { useState } from 'react';\n\nfunction Counter() {\n  const [count, setCount] = useState(0);\n\n  return (\n    <div>\n      <p>Count: {count}</p>\n      <button onClick={() => setCount(count + 1)}>\n        Increment\n      </button>\n    </div>\n  );\n}\n```\n\nIn this example:\n- `useState(0)` initializes the state with a value of 0\n- It returns an array with two elements: the current state value (`count`) and a function to update it (`setCount`)\n- When you click the button, `setCount` is called with the new value, and React re-renders the component",
  },
  {
    id: "5",
    role: "user",
    content: "That's really helpful, thank you!",
  },
  {
    id: "6",
    role: "assistant",
    content:
      "You're welcome! Feel free to ask if you have any more questions about React or programming in general. I'm here to help!",
  },
  {
    id: "7",
    role: "user",
    content: "Can you explain useEffect as well?",
  },
  {
    id: "8",
    role: "assistant",
    content:
      "Absolutely! `useEffect` is a hook that lets you perform side effects in your components. Side effects include things like:\n\n- Fetching data from an API\n- Setting up subscriptions\n- Manually changing the DOM\n- Setting up timers\n\nHere's the basic syntax:\n\n```javascript\nimport { useEffect, useState } from 'react';\n\nfunction Example() {\n  const [count, setCount] = useState(0);\n\n  useEffect(() => {\n    // This runs after every render\n    document.title = `You clicked ${count} times`;\n  });\n\n  return (\n    <button onClick={() => setCount(count + 1)}>\n      Click me\n    </button>\n  );\n}\n```\n\nThe useEffect hook takes two arguments:\n1. A function that contains your side effect code\n2. An optional dependency array that controls when the effect runs",
  },
  {
    id: "9",
    role: "user",
    content: "What's the dependency array for?",
  },
  {
    id: "10",
    role: "assistant",
    content:
      "Great question! The dependency array controls when your effect re-runs. There are three main patterns:\n\n**1. No dependency array** - Effect runs after every render:\n```javascript\nuseEffect(() => {\n  console.log('Runs after every render');\n});\n```\n\n**2. Empty dependency array** - Effect runs only once (on mount):\n```javascript\nuseEffect(() => {\n  console.log('Runs only on mount');\n}, []);\n```\n\n**3. With dependencies** - Effect runs when dependencies change:\n```javascript\nuseEffect(() => {\n  console.log('Runs when count changes');\n}, [count]);\n```\n\nThis optimization helps prevent unnecessary work and potential bugs. You should include all values from the component scope that the effect uses in the dependency array.",
  },
  {
    id: "11",
    role: "user",
    content: "Can you show me a real-world example with data fetching?",
  },
  {
    id: "12",
    role: "assistant",
    content:
      "Sure! Here's a practical example of fetching data with useEffect:\n\n```javascript\nimport { useState, useEffect } from 'react';\n\nfunction UserProfile({ userId }) {\n  const [user, setUser] = useState(null);\n  const [loading, setLoading] = useState(true);\n  const [error, setError] = useState(null);\n\n  useEffect(() => {\n    // Reset state when userId changes\n    setLoading(true);\n    setError(null);\n\n    fetch(`https://api.example.com/users/${userId}`)\n      .then(response => response.json())\n      .then(data => {\n        setUser(data);\n        setLoading(false);\n      })\n      .catch(err => {\n        setError(err.message);\n        setLoading(false);\n      });\n  }, [userId]); // Re-fetch when userId changes\n\n  if (loading) return <div>Loading...</div>;\n  if (error) return <div>Error: {error}</div>;\n  if (!user) return null;\n\n  return (\n    <div>\n      <h1>{user.name}</h1>\n      <p>{user.email}</p>\n    </div>\n  );\n}\n```\n\nThis example shows:\n- Loading states\n- Error handling\n- Dependency tracking (refetches when userId changes)\n- Proper state management",
  },
  {
    id: "13",
    role: "user",
    content: "What about cleanup? I've heard that's important.",
  },
  {
    id: "14",
    role: "assistant",
    content:
      "Excellent point! Cleanup is crucial to prevent memory leaks and unwanted behavior. You can return a cleanup function from your effect:\n\n```javascript\nuseEffect(() => {\n  // Setup\n  const subscription = someAPI.subscribe(data => {\n    console.log(data);\n  });\n\n  // Cleanup function\n  return () => {\n    subscription.unsubscribe();\n  };\n}, []);\n```\n\nCommon cleanup scenarios:\n\n**1. Timers:**\n```javascript\nuseEffect(() => {\n  const timer = setTimeout(() => {\n    console.log('Delayed action');\n  }, 1000);\n\n  return () => clearTimeout(timer);\n}, []);\n```\n\n**2. Event listeners:**\n```javascript\nuseEffect(() => {\n  const handleResize = () => console.log('Resized');\n  window.addEventListener('resize', handleResize);\n\n  return () => window.removeEventListener('resize', handleResize);\n}, []);\n```\n\n**3. Abort fetch requests:**\n```javascript\nuseEffect(() => {\n  const controller = new AbortController();\n\n  fetch('/api/data', { signal: controller.signal })\n    .then(response => response.json())\n    .then(data => setData(data));\n\n  return () => controller.abort();\n}, []);\n```\n\nThe cleanup function runs before the component unmounts and before re-running the effect.",
  },
  {
    id: "15",
    role: "user",
    content: "This is amazing! Do you have any tips for avoiding common mistakes?",
  },
  {
    id: "16",
    role: "assistant",
    content:
      "I'm glad you're finding this helpful! Here are some common pitfalls to avoid:\n\n**1. Missing dependencies:**\n```javascript\n// ❌ Bad - missing 'count' in dependencies\nuseEffect(() => {\n  console.log(count);\n}, []);\n\n// ✅ Good - include all dependencies\nuseEffect(() => {\n  console.log(count);\n}, [count]);\n```\n\n**2. Infinite loops:**\n```javascript\n// ❌ Bad - creates infinite loop\nconst [data, setData] = useState([]);\nuseEffect(() => {\n  setData([...data, 'new item']);\n}); // No dependency array!\n\n// ✅ Good - controlled execution\nuseEffect(() => {\n  fetchData().then(setData);\n}, []); // Runs once\n```\n\n**3. Object/Array dependencies:**\n```javascript\n// ❌ Bad - object recreated every render\nconst options = { limit: 10 };\nuseEffect(() => {\n  fetchData(options);\n}, [options]); // Will run every render!\n\n// ✅ Good - stable reference\nconst options = useMemo(() => ({ limit: 10 }), []);\nuseEffect(() => {\n  fetchData(options);\n}, [options]);\n```\n\n**4. Forgetting cleanup:**\n```javascript\n// ❌ Bad - no cleanup\nuseEffect(() => {\n  const interval = setInterval(() => tick(), 1000);\n}, []); // Memory leak!\n\n// ✅ Good - proper cleanup\nuseEffect(() => {\n  const interval = setInterval(() => tick(), 1000);\n  return () => clearInterval(interval);\n}, []);\n```\n\nRemember: React's ESLint plugin can help catch these issues automatically!",
  },
];

// Dummy conversation history
const baseModels = [
  { value: "gpt-4", label: "GPT-4" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
  { value: "claude-3-opus", label: "Claude 3 Opus" },
  { value: "claude-3-sonnet", label: "Claude 3 Sonnet" },
  { value: "claude-3-haiku", label: "Claude 3 Haiku" },
];

const availableTools = [
  { id: "web-search", label: "Web Search" },
  { id: "code-interpreter", label: "Code Interpreter" },
  { id: "file-browser", label: "File Browser" },
  { id: "calculator", label: "Calculator" },
  { id: "image-generation", label: "Image Generation" },
];

const getModelLabel = (modelValue: string): string => {
  const model = baseModels.find((m) => m.value === modelValue);
  return model?.label || modelValue;
};

const getToolLabel = (toolId: string): string => {
  const tool = availableTools.find((t) => t.id === toolId);
  return tool?.label || toolId;
};

const dummyConversations: Conversation[] = [
  {
    id: "1",
    title: "React Hooks Tutorial",
    preview: "Learning about useState and useEffect...",
    timestamp: "2 hours ago",
  },
  {
    id: "2",
    title: "TypeScript Best Practices",
    preview: "How to structure a TypeScript project",
    timestamp: "Yesterday",
  },
  {
    id: "3",
    title: "Building REST APIs",
    preview: "Express.js and Node.js discussion",
    timestamp: "2 days ago",
  },
  {
    id: "4",
    title: "CSS Grid Layout",
    preview: "Understanding grid-template-areas",
    timestamp: "3 days ago",
  },
  {
    id: "5",
    title: "Database Design",
    preview: "PostgreSQL schema design patterns",
    timestamp: "1 week ago",
  },
  {
    id: "6",
    title: "Git Workflow",
    preview: "Branching strategies and merge conflicts",
    timestamp: "1 week ago",
  },
  {
    id: "7",
    title: "Python Async/Await",
    preview: "Asynchronous programming concepts",
    timestamp: "2 weeks ago",
  },
  {
    id: "8",
    title: "Docker Containers",
    preview: "Containerization and deployment",
    timestamp: "2 weeks ago",
  },
  {
    id: "9",
    title: "GraphQL vs REST",
    preview: "Comparing API architectures",
    timestamp: "3 weeks ago",
  },
  {
    id: "10",
    title: "Web Security",
    preview: "CORS, XSS, and CSRF protection",
    timestamp: "1 month ago",
  },
];

export function ChatView() {
  const [inputValue, setInputValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentConversationId, setCurrentConversationId] = useState("1");
  const [chatSettings, setChatSettings] = useState<ChatSettings>({
    baseModel: "gpt-4",
    systemPrompt:
      "You are a helpful AI assistant. Be concise and informative in your responses.",
    enabledTools: ["web-search", "code-interpreter"],
  });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = Math.min(textarea.scrollHeight, 300);
      textarea.style.height = `${newHeight}px`;
    }
  }, [inputValue]);

  return (
    <div className="relative flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        conversations={dummyConversations}
        currentConversationId={currentConversationId}
        onConversationSelect={setCurrentConversationId}
        onNewConversation={() => console.log("New conversation")}
      />

      {/* Main chat area */}
      <div className="relative flex flex-1 flex-col">
        {/* Header - Sticky at top */}
        <div className="sticky top-0 z-20 shrink-0 border-b border-border bg-muted/30 backdrop-blur-sm px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(true)}
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

        {/* Messages Container */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="mx-auto max-w-3xl pb-6">
            {dummyMessages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
          </div>
        </ScrollArea>

        {/* Input Area - Sticky at bottom */}
        <div className="sticky bottom-0 z-20 shrink-0 border-t border-border bg-background">
          <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1">
                <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{getModelLabel(chatSettings.baseModel)}</span>
              </div>
              {chatSettings.enabledTools.length > 0 && (
                <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1">
                  <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {chatSettings.enabledTools.map((t) => getToolLabel(t)).join(", ")}
                  </span>
                </div>
              )}
            </div>
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your message here..."
                className="min-h-[60px] resize-none pr-24 overflow-y-auto"
                rows={1}
              />
              <div className="absolute bottom-2 right-2 flex gap-1">
                <ChatSettingsDialog
                  settings={chatSettings}
                  onSettingsChange={setChatSettings}
                />
                <Button size="icon" className="h-9 w-9" type="submit">
                  <Send className="h-5 w-5" />
                  <span className="sr-only">Send message</span>
                </Button>
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
