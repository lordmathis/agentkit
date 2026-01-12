import { useState } from "react";
import { Settings } from "lucide-react";
import { Button } from "./ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Switch } from "./ui/switch";

// Dummy data for base models
const baseModels = [
  { value: "gpt-4", label: "GPT-4" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
  { value: "claude-3-opus", label: "Claude 3 Opus" },
  { value: "claude-3-sonnet", label: "Claude 3 Sonnet" },
  { value: "claude-3-haiku", label: "Claude 3 Haiku" },
];

// Dummy data for available tools
const availableTools = [
  { id: "web-search", label: "Web Search", description: "Search the internet" },
  {
    id: "code-interpreter",
    label: "Code Interpreter",
    description: "Execute Python code",
  },
  {
    id: "file-browser",
    label: "File Browser",
    description: "Browse and read files",
  },
  { id: "calculator", label: "Calculator", description: "Perform calculations" },
  {
    id: "image-generation",
    label: "Image Generation",
    description: "Generate images",
  },
];

export interface ChatSettings {
  baseModel: string;
  systemPrompt: string;
  enabledTools: string[];
}

interface ChatSettingsDialogProps {
  settings: ChatSettings;
  onSettingsChange: (settings: ChatSettings) => void;
}

export function ChatSettingsDialog({
  settings,
  onSettingsChange,
}: ChatSettingsDialogProps) {
  const [open, setOpen] = useState(false);
  const [localSettings, setLocalSettings] = useState<ChatSettings>(settings);

  const handleSave = () => {
    onSettingsChange(localSettings);
    setOpen(false);
  };

  const handleCancel = () => {
    setLocalSettings(settings);
    setOpen(false);
  };

  const toggleTool = (toolId: string) => {
    setLocalSettings((prev) => ({
      ...prev,
      enabledTools: prev.enabledTools.includes(toolId)
        ? prev.enabledTools.filter((id) => id !== toolId)
        : [...prev.enabledTools, toolId],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Settings className="h-5 w-5" />
          <span className="sr-only">Chat settings</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Chat Settings</DialogTitle>
          <DialogDescription>
            Configure the base model, system prompt, and available tools for
            this conversation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Base Model Selection */}
          <div className="space-y-2">
            <Label htmlFor="base-model">Base Model</Label>
            <Select
              value={localSettings.baseModel}
              onValueChange={(value) =>
                setLocalSettings((prev) => ({ ...prev, baseModel: value }))
              }
            >
              <SelectTrigger id="base-model" className="w-full">
                <SelectValue placeholder="Select a model" />
              </SelectTrigger>
              <SelectContent>
                {baseModels.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    {model.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* System Prompt */}
          <div className="space-y-2">
            <Label htmlFor="system-prompt">System Prompt</Label>
            <Textarea
              id="system-prompt"
              value={localSettings.systemPrompt}
              onChange={(e) =>
                setLocalSettings((prev) => ({
                  ...prev,
                  systemPrompt: e.target.value,
                }))
              }
              placeholder="Enter system prompt..."
              className="min-h-[120px] resize-none"
              rows={6}
            />
            <p className="text-xs text-muted-foreground">
              The system prompt sets the behavior and context for the AI
              assistant.
            </p>
          </div>

          {/* Tools Section */}
          <div className="space-y-3">
            <Label>Available Tools</Label>
            <p className="text-sm text-muted-foreground">
              Enable or disable tools that the assistant can use during the
              conversation.
            </p>
            <div className="space-y-3 rounded-lg border border-border p-4">
              {availableTools.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-center justify-between space-x-4"
                >
                  <div className="flex-1 space-y-0.5">
                    <Label
                      htmlFor={`tool-${tool.id}`}
                      className="cursor-pointer font-medium"
                    >
                      {tool.label}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {tool.description}
                    </p>
                  </div>
                  <Switch
                    id={`tool-${tool.id}`}
                    checked={localSettings.enabledTools.includes(tool.id)}
                    onCheckedChange={() => toggleTool(tool.id)}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-border">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
