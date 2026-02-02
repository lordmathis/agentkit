import { useEffect } from "react";
import { Github, Loader2 } from "lucide-react";
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
import { TreeNode } from "./github/tree-node";
import { RepoSelector } from "./github/repo-selector";
import { SelectionSummary } from "./github/selection-summary";
import { useGitHubDialog } from "../hooks/use-github-dialog";

interface AddGitHubDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chatId?: string;
  onFilesAdded?: (repo: string, paths: string[], excludePaths: string[], count: number) => void;
  initialRepo?: string;
  initialPaths?: string[];
  initialExcludePaths?: string[];
}

export function AddGitHubDialog({
  open,
  onOpenChange,
  chatId,
  onFilesAdded,
  initialRepo = "",
  initialPaths = [],
  initialExcludePaths = [],
}: AddGitHubDialogProps) {
  const {
    inputMode,
    setInputMode,
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
  } = useGitHubDialog(initialRepo, initialPaths, initialExcludePaths);

  useEffect(() => {
    if (open && inputMode === "select" && repositories.length === 0) {
      loadRepositories();
    }
  }, [open, inputMode]);

  const handleAdd = async () => {
    const success = await handleAddFiles(chatId, (repo, paths, excludePaths, count) => {
      onFilesAdded?.(repo, paths, excludePaths, count);
    });

    if (success) {
      onOpenChange(false);
    }
  };

  const handleClose = () => {
    setError("");
    onOpenChange(false);
  };

  const includedCount = Array.from(selectedPaths).filter((p) => !p.startsWith("!")).length;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Github className="h-5 w-5" />
            Add from GitHub
          </DialogTitle>
          <DialogDescription>
            Select files from a GitHub repository to add to your chat context
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-4">
          <RepoSelector
            inputMode={inputMode}
            setInputMode={setInputMode}
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

          <SelectionSummary selectedPaths={selectedPaths} tokenEstimate={tokenEstimate} />
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
