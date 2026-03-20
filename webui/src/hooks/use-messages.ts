import { useState, useEffect, useCallback } from "react";
import { api, type Message, type FileResource } from "../lib/api";
import { type ChatSettings } from "../components/chat-settings-dialog";

export function useMessages(chatId: string | undefined) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [chatSettings, setChatSettings] = useState<ChatSettings>({
    baseModel: "",
    systemPrompt: "",
    enabledTools: [],
    modelParams: {
      max_iterations: 5,
    },
  });

  const reloadMessages = useCallback(async () => {
    if (!chatId) return;
    try {
      const chatData = await api.getChat(chatId);
      setMessages(chatData.messages);
      setChatSettings({
        baseModel: chatData.model || "",
        systemPrompt: chatData.system_prompt || "",
        enabledTools: chatData.tool_servers || [],
        modelParams: chatData.model_params || {
          max_iterations: 5,
        },
      });
    } catch (error) {
      console.error("Failed to reload messages:", error);
    }
  }, [chatId]);

  useEffect(() => {
    if (!chatId) {
      setMessages([]);
      return;
    }
    const fetchInitial = async () => {
      setIsLoading(true);
      await reloadMessages();
      setIsLoading(false);
    };
    fetchInitial();
  }, [chatId, reloadMessages]);

  const send = async (text: string, files: FileResource[]) => {
    if (!chatId) return;
    
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage: Message = {
      id: tempId,
      role: 'user',
      content: text,
      sequence: messages.length,
      created_at: new Date().toISOString(),
      files: files.map(f => ({
        id: f.id,
        filename: f.filename,
        content_type: f.content_type,
      })),
    };
    
    setMessages(prev => [...prev, optimisticMessage]);
    
    try {
      setIsSending(true);
      await api.sendMessage(chatId, {
        message: text,
        file_ids: files.map(f => f.id),
        stream: false,
      });
      await reloadMessages();
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== tempId));
      throw error;
    } finally {
      setIsSending(false);
    }
  };

  const retry = async () => {
    if (!chatId) return;
    try {
      setIsSending(true);
      await api.retryLastMessage(chatId);
      await reloadMessages();
    } finally {
      setIsSending(false);
    }
  };

  const edit = async (text: string) => {
    if (!chatId) return;
    try {
      setIsSending(true);
      await api.editLastMessage(chatId, text);
      await reloadMessages();
    } finally {
      setIsSending(false);
    }
  };

  return {
    messages,
    isLoading,
    isSending,
    chatSettings,
    setChatSettings,
    send,
    retry,
    edit,
  };
}
