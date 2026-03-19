import { useState, useRef, useCallback } from "react";
import type { Message } from "../lib/api";

interface UseChatInputOptions {
  onSend: (text: string, fileIds: string[]) => Promise<void>;
  onEdit: (text: string) => Promise<void>;
  messages: Message[];
  getFileIds: () => string[];
  isSending: boolean;
  onSendComplete?: () => void;
  onEditComplete?: () => void;
}

interface UseChatInputReturn {
  inputValue: string;
  setInputValue: (value: string) => void;
  isEditingMode: boolean;
  handleSend: () => Promise<void>;
  handleEdit: () => void;
  cancelEdit: () => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function useChatInput({
  onSend,
  onEdit,
  messages,
  getFileIds,
  isSending,
  onSendComplete,
  onEditComplete,
}: UseChatInputOptions): UseChatInputReturn {
  const [inputValue, setInputValue] = useState("");
  const [isEditingMode, setIsEditingMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isSending) return;

    const text = inputValue.trim();
    const fileIds = getFileIds();

    setInputValue("");

    if (isEditingMode) {
      await onEdit(text);
      setIsEditingMode(false);
      onEditComplete?.();
    } else {
      await onSend(text, fileIds);
      onSendComplete?.();
    }
  }, [inputValue, isSending, getFileIds, isEditingMode, onSend, onEdit, onSendComplete, onEditComplete]);

  const handleEdit = useCallback(() => {
    const lastUserMessage = [...messages].reverse().find((msg) => msg.role === "user");

    if (!lastUserMessage) return;

    setInputValue(lastUserMessage.content);
    setIsEditingMode(true);
    textareaRef.current?.focus();
  }, [messages]);

  const cancelEdit = useCallback(() => {
    setInputValue("");
    setIsEditingMode(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return {
    inputValue,
    setInputValue,
    isEditingMode,
    handleSend,
    handleEdit,
    cancelEdit,
    handleKeyDown,
    textareaRef,
  };
}