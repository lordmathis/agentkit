import { useState, useEffect } from "react";
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
import { api, type Model, type ToolServer } from "../lib/api";

export interface ChatSettings {
  baseModel: string;
  systemPrompt: string;
  enabledTools: string[];
}

interface ChatSettingsDialogProps {
  settings: ChatSettings;
  onSettingsChange: (settings: ChatSettings) => void;
  currentChatId?: string; // Optional chat ID for updating existing chats
  onChatUpdated?: () => void; // Callback when chat is updated on backend
}

export function ChatSettingsDialog({
  settings,
  onSettingsChange,
  currentChatId,
  onChatUpdated,
}: ChatSettingsDialogProps) {
  const [open, setOpen] = useState(false);
  const [localSettings, setLocalSettings] = useState<ChatSettings>(settings);
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, { id: string; label: string }[]>>({});
  const [providers, setProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [toolServers, setToolServers] = useState<ToolServer[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isLoadingTools, setIsLoadingTools] = useState(false);

  // Fetch tools immediately when dialog opens, then models after
  useEffect(() => {
    if (open) {
      // Load tools first (fast) so they appear immediately
      fetchTools().then(() => {
        // Load models after tools finish (slower, won't block tools UI)
        fetchModels();
      });
    }
  }, [open]);

  // Sync local settings when parent settings change
  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const fetchModels = async () => {
    try {
      setIsLoadingModels(true);
      const response = await api.listModels();

      // Group models by provider
      const grouped: Record<string, { id: string; label: string }[]> = {};
      response.data.forEach((model: Model) => {
        const provider = model.owned_by || "Unknown";
        if (!grouped[provider]) {
          grouped[provider] = [];
        }
        grouped[provider].push({
          id: model.id,
          label: model.id,
        });
      });

      setModelsByProvider(grouped);
      const providerList = Object.keys(grouped).sort();
      setProviders(providerList);

      // Determine the initial provider based on current model
      if (localSettings.baseModel) {
        const currentProvider = response.data.find(
          (m: Model) => m.id === localSettings.baseModel
        )?.owned_by || "";
        setSelectedProvider(currentProvider);
      } else if (providerList.length > 0) {
        // Set default provider and model if none selected
        setSelectedProvider(providerList[0]);
        const firstProvider = providerList[0];
        const firstModel = grouped[firstProvider]?.[0];
        if (firstModel) {
          setLocalSettings((prev) => ({
            ...prev,
            baseModel: firstModel.id,
          }));
        }
      }
    } catch (error) {
      console.error("Failed to fetch models:", error);
      setModelsByProvider({});
      setProviders([]);
    } finally {
      setIsLoadingModels(false);
    }
  };

  const fetchTools = async () => {
    try {
      setIsLoadingTools(true);
      const response = await api.listTools();
      setToolServers(response.tool_servers);
    } catch (error) {
      console.error("Failed to fetch tools:", error);
      setToolServers([]);
    } finally {
      setIsLoadingTools(false);
    }
  };

  const handleSave = async () => {
    // Update local state first
    onSettingsChange(localSettings);
    
    // If there's a current chat, update it on the backend
    if (currentChatId) {
      try {
        await api.updateChat(currentChatId, {
          config: {
            model: localSettings.baseModel,
            system_prompt: localSettings.systemPrompt || undefined,
            tool_servers: localSettings.enabledTools.length > 0 ? localSettings.enabledTools : undefined,
          },
        });
        // Notify parent that chat was updated
        onChatUpdated?.();
      } catch (error) {
        console.error("Failed to update chat settings:", error);
        alert(`Failed to update chat settings: ${error instanceof Error ? error.message : "Unknown error"}`);
        return; // Don't close dialog on error
      }
    }
    
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
          {/* Provider Selection */}
          <div className="space-y-2">
            <Label htmlFor="provider">Provider</Label>
            <Select
              value={selectedProvider}
              onValueChange={(value) => {
                setSelectedProvider(value);
                // Reset model selection when provider changes
                const modelsForProvider = modelsByProvider[value] || [];
                if (modelsForProvider.length > 0 && !modelsForProvider.find(m => m.id === localSettings.baseModel)) {
                  setLocalSettings((prev) => ({ ...prev, baseModel: modelsForProvider[0].id }));
                }
              }}
              disabled={isLoadingModels}
            >
              <SelectTrigger id="provider" className="w-full">
                <SelectValue placeholder={isLoadingModels ? "Loading providers..." : "Select a provider"} />
              </SelectTrigger>
              <SelectContent>
                {providers.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Base Model Selection */}
          <div className="space-y-2">
            <Label htmlFor="base-model">Base Model</Label>
            <Select
              value={localSettings.baseModel}
              onValueChange={(value) =>
                setLocalSettings((prev) => ({ ...prev, baseModel: value }))
              }
              disabled={isLoadingModels || !selectedProvider}
            >
              <SelectTrigger id="base-model" className="w-full">
                <SelectValue placeholder={isLoadingModels ? "Loading models..." : "Select a model"} />
              </SelectTrigger>
              <SelectContent>
                {(modelsByProvider[selectedProvider] || []).map((model) => (
                  <SelectItem key={model.id} value={model.id}>
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
            <Label>Tool Servers</Label>
            <p className="text-sm text-muted-foreground">
              Select which tool servers the assistant can use during the conversation.
            </p>
            {isLoadingTools ? (
              <div className="rounded-lg border border-border p-4 text-center text-sm text-muted-foreground">
                Loading available tools...
              </div>
            ) : toolServers.length === 0 ? (
              <div className="rounded-lg border border-border p-4 text-center text-sm text-muted-foreground">
                No tool servers available
              </div>
            ) : (
              <div className="space-y-3 rounded-lg border border-border p-4">
                {toolServers.map((server) => (
                  <div
                    key={server.name}
                    className="flex items-center justify-between space-x-4"
                  >
                    <div className="flex-1 space-y-0.5">
                      <Label
                        htmlFor={`tool-${server.name}`}
                        className="cursor-pointer font-medium"
                      >
                        {server.name}
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        {server.tools.length} tool{server.tools.length !== 1 ? 's' : ''} available ({server.type})
                      </p>
                    </div>
                    <Switch
                      id={`tool-${server.name}`}
                      checked={localSettings.enabledTools.includes(server.name)}
                      onCheckedChange={() => toggleTool(server.name)}
                    />
                  </div>
                ))}
              </div>
            )}
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
