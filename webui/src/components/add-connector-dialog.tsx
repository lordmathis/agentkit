import { useEffect, useState } from "react";
import { Loader2, Filter, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { TreeNode } from "./connector/tree-node";
import { ConnectorSelector } from "./connector/connector-selector";
import { SelectionSummary } from "./connector/selection-summary";
import { useConnectorDialog } from "../hooks/use-connector-dialog";

interface AddConnectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chatId?: string;
  onFilesAdded?: (connectorId: string, resourceId: string, paths: string[], excludePaths: string[], files: import('../lib/api').FileResource[]) => void;
  initialInstance?: string;
  initialConnector?: string;
  initialPaths?: string[];
  initialExcludePaths?: string[];
}

export function AddConnectorDialog({
  open,
  onOpenChange,
  chatId,
  onFilesAdded,
  initialInstance = "",
  initialConnector = "",
  initialPaths = [],
  initialExcludePaths = [],
}: AddConnectorDialogProps) {
  const {
    inputMode,
    setInputMode,
    connectors,
    selectedConnector,
    setSelectedConnector,
    isLoadingConnectors,
    resources,
    selectedResource,
    setSelectedResource,
    resourceLink,
    setResourceLink,
    isLoadingResources,
    isLoadingTree,
    loadingPaths,
    treeRoot,
    expandedPaths,
    selectedPaths,
    isAdding,
    error,
    tokenEstimate,
isEstimatingTokens,
    loadResources,
    loadChildren,
    toggleExpand,
    isPathSelected,
    isPathExcluded,
    toggleSelect,
    handleAddFiles,
    handleResourceSelect,
    handleLinkPaste,
  } = useConnectorDialog(initialInstance, initialConnector, initialPaths, initialExcludePaths);

  const [filterPattern, setFilterPattern] = useState("");
  const [isApplyingFilter, setIsApplyingFilter] = useState(false);

  const applyFilter = () => {
    setIsApplyingFilter(true);
    setTimeout(() => setIsApplyingFilter(false), 500);
  };

  useEffect(() => {
    if (open && inputMode === "select" && resources.length === 0 && selectedConnector) {
      loadResources();
    }
  }, [open, inputMode, selectedConnector, resources.length]);

  const includedCount = Array.from(selectedPaths).filter(p => !p.startsWith("!")).length;

  const handleAdd = async () => {
    const files = await handleAddFiles(chatId, (resource, paths, excludePaths, _count) => {
      onFilesAdded?.(selectedConnector, resource, paths, excludePaths, []);
    });
    if (files) {
      onOpenChange(false);
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
            inputMode={inputMode}
            setInputMode={setInputMode}
            connectors={connectors}
            selectedConnector={selectedConnector}
            setSelectedConnector={setSelectedConnector}
            isLoadingConnectors={isLoadingConnectors}
            selectedResource={selectedResource}
            setSelectedResource={setSelectedResource}
            resourceLink={resourceLink}
            setResourceLink={setResourceLink}
            resources={resources}
            isLoadingResources={isLoadingResources}
            isLoadingTree={isLoadingTree}
            onResourceSelect={handleResourceSelect}
            onLinkPaste={handleLinkPaste}
          />

          {treeRoot && (
            <div className="flex gap-2 items-start">
              <div className="relative flex-1 min-w-0">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none z-10" />
                <Input
                  placeholder="Filter files (e.g., *.test.py, uv.lock, *lock.json)"
                  value={filterPattern}
                  onChange={(e) => setFilterPattern(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      applyFilter();
                    }
                  }}
                  className="pl-9 pr-9"
                />
                {filterPattern && (
                  <button
                    onClick={() => setFilterPattern("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground z-10"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <Button
                variant="outline"
                onClick={applyFilter}
                disabled={!filterPattern.trim() || isApplyingFilter}
              >
                {isApplyingFilter ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Applying...
                  </>
                ) : (
                  "Apply"
                )}
              </Button>
            </div>
          )}

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">{error}</div>
          )}

          {treeRoot && (
            <div className="flex-1 min-h-0 border rounded-md">
              <ScrollArea className="h-[300px] p-2">
                <TreeNode
                  node={treeRoot}
                  level={0}
                  selectedPaths={selectedPaths}
                  expandedPaths={expandedPaths}
                  onToggleSelect={toggleSelect}
                  onToggleExpand={toggleExpand}
                  onLoadChildren={loadChildren}
                  loadingPaths={loadingPaths}
                  isPathSelected={isPathSelected}
                  isPathExcluded={isPathExcluded}
                />
              </ScrollArea>
            </div>
          )}

          <SelectionSummary selectedPaths={selectedPaths} tokenEstimate={tokenEstimate} isEstimatingTokens={isEstimatingTokens} />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isAdding}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={isAdding || selectedPaths.size === 0 || !chatId}>
            {isAdding ? (
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
