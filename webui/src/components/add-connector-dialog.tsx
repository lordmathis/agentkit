import { useEffect, useState } from "react";
import { Github, Loader2, Filter, X, Link as LinkIcon } from "lucide-react";
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
import { api } from "../lib/api";

interface AddConnectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chatId?: string;
  onFilesAdded?: (repo: string, paths: string[], excludePaths: string[], files: import('../lib/api').FileResource[]) => void;
  initialConnector?: string;
  initialRepo?: string;
  initialPaths?: string[];
  initialExcludePaths?: string[];
}

export function AddConnectorDialog({
  open,
  onOpenChange,
  chatId,
  onFilesAdded,
  initialConnector = "",
  initialRepo = "",
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
    repositories,
    selectedRepo,
    setSelectedRepo,
    repoLink,
    setRepoLink,
    isLoadingRepos,
    isLoadingTree,
    loadingPaths,
    treeRoot,
    expandedPaths,
    selectedPaths,
    isAdding,
    error,
    setError,
    tokenEstimate,
    isEstimatingTokens,
    getRepoIdentifier,
    loadRepositories,
    loadTree,
    loadChildren,
    toggleExpand,
    isPathSelected,
    isPathExcluded,
    toggleSelect,
    handleAddFiles,
    handleRepoSelect,
    handleLinkPaste,
  } = useConnectorDialog(initialConnector, initialRepo, initialPaths, initialExcludePaths);

  const [filterPattern, setFilterPattern] = useState("");
  const [isApplyingFilter, setIsApplyingFilter] = useState(false);

  // Helper function to match a file path against a pattern
  const matchesPattern = (filePath: string, pattern: string): boolean => {
    if (!pattern.trim()) return false;
    
    const fileName = filePath.split('/').pop() || filePath;
    const normalizedPattern = pattern.trim();
    
    // Exact match
    if (fileName === normalizedPattern || filePath === normalizedPattern) {
      return true;
    }
    
    // Wildcard pattern matching
    const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const patternRegex = new RegExp(
      '^' + normalizedPattern.split('*').map(escapeRegex).join('.*') + '$'
    );
    
    return patternRegex.test(fileName) || patternRegex.test(filePath);
  };

  // Recursively fetch all file paths using the API directly
  const fetchAllFilePaths = async (repo: string, path: string = ""): Promise<string[]> => {
    const paths: string[] = [];
    
    try {
      const node = await api.browseConnectorTree(selectedConnector, repo, path);
      
      if (node.type === 'file') {
        paths.push(node.path);
      } else if (node.children) {
        for (const child of node.children) {
          if (child.type === 'file') {
            paths.push(child.path);
          } else if (child.type === 'dir') {
            // Recursively fetch paths from subdirectories
            const subPaths = await fetchAllFilePaths(repo, child.path);
            paths.push(...subPaths);
          }
        }
      }
    } catch (err) {
      console.error(`Failed to fetch paths for ${path}:`, err);
    }
    
    return paths;
  };

  // Apply the filter pattern
  const applyFilter = async () => {
    if (!filterPattern.trim() || !treeRoot) return;
    
    const repo = getRepoIdentifier();
    if (!repo) return;
    
    setIsApplyingFilter(true);
    setError(""); // Clear any previous errors
    
    try {
      // Fetch all file paths recursively using the API
      const allFilePaths = await fetchAllFilePaths(repo);
      const matchingPaths = allFilePaths.filter(path => matchesPattern(path, filterPattern));
      
      // Uncheck all matching files
      matchingPaths.forEach(path => {
        const isCurrentlySelected = isPathSelected(path);
        const isCurrentlyExcluded = isPathExcluded(path);
        
        // If file is selected and not already excluded, toggle it to uncheck
        if (isCurrentlySelected && !isCurrentlyExcluded) {
          toggleSelect(path, false);
        }
      });
      
      setFilterPattern(""); // Clear the filter input after applying
    } catch (err) {
      setError("Failed to fetch repository files. Please try again.");
    } finally {
      setIsApplyingFilter(false);
    }
  };

  useEffect(() => {
    if (open && inputMode === "select" && repositories.length === 0 && selectedConnector) {
      loadRepositories();
    }
  }, [open, inputMode, selectedConnector]);

  const handleAdd = async () => {
    const result = await handleAddFiles(chatId, () => {});

    if (result) {
      onFilesAdded?.(getRepoIdentifier() || "", Array.from(selectedPaths).filter(p => !p.startsWith('!')), Array.from(selectedPaths).filter(p => p.startsWith('!')).map(p => p.substring(1)), result);
      onOpenChange(false);
    }
  };

  const handleClose = () => {
    setError("");
    onOpenChange(false);
  };

  const includedCount = Array.from(selectedPaths).filter((p) => !p.startsWith("!")).length;

  const currentConnector = connectors.find(c => c.name === selectedConnector);
  const Icon = currentConnector?.type === 'github' ? Github : LinkIcon;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Icon className="h-5 w-5" />
            Add from {currentConnector ? `${currentConnector.name}` : 'Connector'}
          </DialogTitle>
          <DialogDescription>
            Select files from a repository to add to your chat context
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-4 px-1 -mx-1">
          <ConnectorSelector
            inputMode={inputMode}
            setInputMode={setInputMode}
            connectors={connectors}
            selectedConnector={selectedConnector}
            setSelectedConnector={setSelectedConnector}
            isLoadingConnectors={isLoadingConnectors}
            selectedRepo={selectedRepo}
            setSelectedRepo={setSelectedRepo}
            repoLink={repoLink}
            setRepoLink={setRepoLink}
            repositories={repositories}
            isLoadingRepos={isLoadingRepos}
            isLoadingTree={isLoadingTree}
            onRepoSelect={handleRepoSelect}
            onLinkPaste={handleLinkPaste}
            getRepoIdentifier={getRepoIdentifier}
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
