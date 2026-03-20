import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { TreeNode } from "./connector/tree-node";
import { ConnectorSelector } from "./connector/connector-selector";
import { SelectionSummary } from "./connector/selection-summary";
import { usePathSelection } from "../hooks/use-path-selection";
import { useConnectorData } from "../hooks/use-connector-data";
import type { ConnectorEntry } from "../lib/api";

interface AddConnectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chatId?: string;
  onFilesAdded?: (entry: ConnectorEntry) => void;
  editingEntry?: ConnectorEntry;
}

export function AddConnectorDialog({
  open,
  onOpenChange,
  chatId,
  onFilesAdded,
  editingEntry,
}: AddConnectorDialogProps) {
  const pathSelection = usePathSelection(
    editingEntry?.paths || [],
    editingEntry?.excludePaths || []
  );
  const connectorData = useConnectorData(
    editingEntry?.connectorId || "",
    editingEntry?.resourceId || "",
    pathSelection.includedPaths,
    pathSelection.excludedPaths
  );

  const handleToggleSelect = (path: string, isDir: boolean) =>
    pathSelection.toggleSelect(path, isDir, connectorData.treeRoot);

  useEffect(() => {
    if (open && connectorData.inputMode === "select" && connectorData.resources.length === 0 && connectorData.selectedConnector) {
      connectorData.loadResources();
    }
  }, [open, connectorData.inputMode, connectorData.selectedConnector, connectorData.resources.length]);

  const includedCount = Array.from(pathSelection.selectedPaths).filter(p => !p.startsWith("!")).length;

  const handleAdd = async () => {
    if (!chatId) return;
    
    try {
      const files = await connectorData.uploadFiles(
        pathSelection.includedPaths,
        pathSelection.excludedPaths
      );
      onFilesAdded?.({
        connectorId: connectorData.selectedConnector,
        resourceId: connectorData.getResourceIdentifier(),
        paths: pathSelection.includedPaths,
        excludePaths: pathSelection.excludedPaths,
        files,
      });
      onOpenChange(false);
    } catch {
      // Error already set in hook
    }
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Add Connector Files</DialogTitle>
          <DialogDescription>
            Select files from a repository to add to your conversation
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 flex flex-col gap-4 overflow-hidden">
          <ConnectorSelector
            inputMode={connectorData.inputMode}
            setInputMode={connectorData.setInputMode}
            connectors={connectorData.connectors}
            selectedConnector={connectorData.selectedConnector}
            setSelectedConnector={connectorData.setSelectedConnector}
            isLoadingConnectors={connectorData.isLoadingConnectors}
            selectedResource={connectorData.selectedResource}
            setSelectedResource={connectorData.setSelectedResource}
            resourceLink={connectorData.resourceLink}
            setResourceLink={connectorData.setResourceLink}
            resources={connectorData.resources}
            isLoadingResources={connectorData.isLoadingResources}
            isLoadingTree={connectorData.isLoadingTree}
            onResourceSelect={connectorData.handleResourceSelect}
            onLinkPaste={connectorData.handleLinkPaste}
          />

          {connectorData.error && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">{connectorData.error}</div>
          )}

          {connectorData.treeRoot && (
            <div className="flex-1 min-h-0 border rounded-md">
              <ScrollArea className="h-[300px] p-2">
                <TreeNode
                  node={connectorData.treeRoot}
                  level={0}
                  selectedPaths={pathSelection.selectedPaths}
                  expandedPaths={connectorData.expandedPaths}
                  onToggleSelect={handleToggleSelect}
                  onToggleExpand={connectorData.toggleExpand}
                  onLoadChildren={connectorData.loadChildren}
                  loadingPaths={connectorData.loadingPaths}
                  isPathSelected={pathSelection.isPathSelected}
                  isPathExcluded={pathSelection.isPathExcluded}
                />
              </ScrollArea>
            </div>
          )}

          <SelectionSummary selectedPaths={pathSelection.selectedPaths} tokenEstimate={connectorData.tokenEstimate} isEstimatingTokens={connectorData.isEstimatingTokens} />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={connectorData.isAdding}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={connectorData.isAdding || pathSelection.selectedPaths.size === 0 || !chatId}>
            {connectorData.isAdding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Adding files...
              </>
            ) : (
              `Add ${includedCount} item${includedCount !== 1 ? "s" : ""}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
