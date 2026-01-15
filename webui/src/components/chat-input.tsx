import { Send, Bot, Zap, Plus, Upload, Github } from "lucide-react";
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
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type your message here..."
            className="min-h-[60px] resize-none pr-32 overflow-y-auto"
            rows={1}
            disabled={isSending || !currentConversationId}
          />

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
