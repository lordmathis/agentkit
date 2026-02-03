import { Send, Bot, Zap, Plus, Upload, Github, Mic, Square, AtSign } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { ChatSettingsDialog, type ChatSettings } from "./chat-settings-dialog";
import { FileAttachments } from "./file-attachments";
import { getModelLabel, getToolLabel } from "../lib/formatters";
import { useVoiceRecording } from "../hooks/use-voice-recording";
import { api, type Skill } from "../lib/api";
import { useEffect, useState } from "react";

interface ChatInputProps {
  inputValue: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  isSending: boolean;
  isUploadingFiles: boolean;
  currentConversationId: string | undefined;
  chatSettings: ChatSettings;
  onSettingsChange: (settings: ChatSettings) => void;
  uploadedFiles: string[];
  githubFiles: { repo: string; paths: string[]; excludePaths: string[] };
  onRemoveFile: (filename: string) => void;
  onRemoveGitHubFiles: () => void;
  onFileUploadClick: () => void;
  onGitHubDialogOpen: () => void;
  onChatUpdated: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function ChatInput({
  inputValue,
  onInputChange,
  onSend,
  onKeyDown,
  isSending,
  isUploadingFiles,
  currentConversationId,
  chatSettings,
  onSettingsChange,
  uploadedFiles,
  githubFiles,
  onRemoveFile,
  onRemoveGitHubFiles,
  onFileUploadClick,
  onGitHubDialogOpen,
  onChatUpdated,
  textareaRef,
  fileInputRef,
  onFileChange,
}: ChatInputProps) {
  const {
    isRecording,
    isProcessing,
    error: recordingError,
    startRecording,
    stopRecording,
    setProcessing,
    clearError,
  } = useVoiceRecording();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState("");
  const [mentionStart, setMentionStart] = useState(-1);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);

  // Load skills
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const result = await api.listSkills();
        setSkills(result.skills);
      } catch (error) {
        console.error('Failed to load skills:', error);
      }
    };
    loadSkills();
  }, []);

  // Filter skills based on search
  const filteredSkills = skills.filter(skill => 
    skill.name.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  // Show error message if recording fails
  useEffect(() => {
    if (recordingError) {
      console.error('Voice recording error:', recordingError);
      setTimeout(clearError, 5000);
    }
  }, [recordingError, clearError]);

  const handleInputChangeWithMentions = (value: string) => {
    onInputChange(value);
    
    const cursorPos = textareaRef.current?.selectionStart || 0;
    const textBeforeCursor = value.substring(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    if (lastAtIndex !== -1) {
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      if (!textAfterAt.includes(' ') && !textAfterAt.includes('\n')) {
        setShowMentions(true);
        setMentionSearch(textAfterAt);
        setMentionStart(lastAtIndex);
        setSelectedMentionIndex(0);
        return;
      }
    }
    
    setShowMentions(false);
  };

  const insertMention = (skillName: string) => {
    if (mentionStart === -1) return;
    
    const before = inputValue.substring(0, mentionStart);
    const cursorPos = textareaRef.current?.selectionStart || 0;
    const after = inputValue.substring(cursorPos);
    
    const newValue = `${before}@${skillName} ${after}`;
    onInputChange(newValue);
    setShowMentions(false);
    
    // Focus textarea and set cursor position
    setTimeout(() => {
      textareaRef.current?.focus();
      const newCursorPos = mentionStart + skillName.length + 2;
      textareaRef.current?.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  const handleKeyDownWithMentions = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentions && filteredSkills.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedMentionIndex(prev => Math.min(prev + 1, filteredSkills.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedMentionIndex(prev => Math.max(prev - 1, 0));
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        insertMention(filteredSkills[selectedMentionIndex].name);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowMentions(false);
        return;
      }
    }
    
    onKeyDown(e);
  };

  const handleVoiceRecording = async () => {
    if (isRecording) {
      // Stop recording and transcribe
      try {
        setProcessing(true);
        const audioBlob = await stopRecording();
        
        // Send to transcription endpoint
        const result = await api.transcribeAudio(audioBlob);
        
        // Add transcribed text to the input
        onInputChange(inputValue + (inputValue ? ' ' : '') + result.text);
        
        // Focus the textarea
        textareaRef.current?.focus();
      } catch (err) {
        console.error('Failed to transcribe audio:', err);
      } finally {
        setProcessing(false);
      }
    } else {
      // Start recording
      try {
        await startRecording();
      } catch (err) {
        console.error('Failed to start recording:', err);
      }
    }
  };

  return (
    <div className="sticky bottom-0 z-20 shrink-0 border-t border-border bg-background">
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
        {/* Model and tools info */}
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

        {/* File attachments */}
        <FileAttachments
          uploadedFiles={uploadedFiles}
          githubFiles={githubFiles}
          onRemoveFile={onRemoveFile}
          onRemoveGitHubFiles={onRemoveGitHubFiles}
          onEditGitHubFiles={onGitHubDialogOpen}
        />

        {/* Input area */}
        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => handleInputChangeWithMentions(e.target.value)}
            onKeyDown={handleKeyDownWithMentions}
            placeholder="Type your message... (use @ to mention skills)"
            className="min-h-[60px] resize-none pr-32 overflow-y-auto"
            rows={1}
            disabled={isSending || !currentConversationId}
          />

          {/* Skills mention popover */}
          {showMentions && filteredSkills.length > 0 && (
            <div className="absolute bottom-full left-0 mb-2 w-64 rounded-md border border-border bg-popover shadow-lg z-50">
              <div className="max-h-60 overflow-y-auto p-1">
                {filteredSkills.map((skill, index) => (
                  <button
                    key={skill.name}
                    type="button"
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm transition-colors text-left ${
                      index === selectedMentionIndex
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-accent/50'
                    }`}
                    onClick={() => insertMention(skill.name)}
                    onMouseEnter={() => setSelectedMentionIndex(index)}
                  >
                    <AtSign className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="truncate font-medium">{skill.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={onFileChange}
          />

          {/* Action buttons */}
          <div className="absolute bottom-2 right-2 flex gap-1">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-9 w-9"
                  disabled={isSending || isUploadingFiles || !currentConversationId}
                >
                  <Plus className="h-5 w-5" />
                  <span className="sr-only">Add attachments</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" side="top">
                <DropdownMenuItem onClick={onFileUploadClick} disabled={isUploadingFiles}>
                  <Upload className="mr-2 h-4 w-4" />
                  <span>{isUploadingFiles ? "Uploading..." : "Upload files"}</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onGitHubDialogOpen}>
                  <Github className="mr-2 h-4 w-4" />
                  <span>Add from GitHub</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              size="icon"
              variant={isRecording ? "destructive" : "ghost"}
              className="h-9 w-9"
              onClick={handleVoiceRecording}
              disabled={isSending || isProcessing || !currentConversationId}
            >
              {isRecording ? (
                <Square className="h-5 w-5" />
              ) : (
                <Mic className="h-5 w-5" />
              )}
              <span className="sr-only">
                {isRecording ? 'Stop recording' : 'Start voice recording'}
              </span>
            </Button>
            <ChatSettingsDialog
              settings={chatSettings}
              onSettingsChange={onSettingsChange}
              currentChatId={currentConversationId}
              onChatUpdated={onChatUpdated}
            />
            <Button
              size="icon"
              className="h-9 w-9"
              type="submit"
              onClick={onSend}
              disabled={isSending || !currentConversationId || !inputValue.trim()}
            >
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
  );
}
