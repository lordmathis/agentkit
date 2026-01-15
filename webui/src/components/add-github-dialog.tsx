import { useState, useEffect } from "react";
import { Github, Folder, File, ChevronRight, ChevronDown, Loader2 } from "lucide-react";
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
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { ScrollArea } from "./ui/scroll-area";
import { Checkbox } from "./ui/checkbox";
import { api, type GitHubRepository, type FileNode } from "../lib/api";

interface AddGitHubDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chatId?: string;
  onFilesAdded?: (repo: string, paths: string[], excludePaths: string[], count: number) => void;
  initialRepo?: string;
  initialPaths?: string[];
  initialExcludePaths?: string[];
}

interface TreeNodeProps {
  node: FileNode;
  level: number;
  selectedPaths: Set<string>;
  expandedPaths: Set<string>;
  onToggleSelect: (path: string, isDir: boolean) => void;
  onToggleExpand: (path: string) => void;
  onLoadChildren: (path: string) => void;
  loadingPaths: Set<string>;
  isPathSelected: (path: string) => boolean;
  isPathExcluded: (path: string) => boolean;
}

function TreeNode({
  node,
  level,
  selectedPaths,
  expandedPaths,
  onToggleSelect,
  onToggleExpand,
  onLoadChildren,
  loadingPaths,
  isPathSelected,
  isPathExcluded,
}: TreeNodeProps) {
  const isExpanded = expandedPaths.has(node.path);
  const isLoading = loadingPaths.has(node.path);
  const isSelected = isPathSelected(node.path);
  const isExcluded = isPathExcluded(node.path);
  const isDir = node.type === "dir";

  const handleToggle = () => {
    if (isDir) {
      if (!isExpanded && !node.children) {
        onLoadChildren(node.path);
      }
      onToggleExpand(node.path);
    }
  };

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 px-2 hover:bg-accent rounded-md cursor-pointer"
        style={{ paddingLeft: `${level * 20 + 8}px` }}
      >
        {isDir && (
          <button
            onClick={handleToggle}
            className="flex items-center justify-center w-4 h-4 hover:bg-accent-foreground/10 rounded"
          >
            {isLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </button>
        )}
        {!isDir && <div className="w-4" />}
        <Checkbox
          checked={isSelected && !isExcluded}
          onCheckedChange={() => onToggleSelect(node.path, isDir)}
          className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
        />
        {isDir ? (
          <Folder className="h-4 w-4 text-blue-500 flex-shrink-0" />
        ) : (
          <File className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
        <span className="text-sm truncate" onClick={handleToggle}>
          {node.name}
        </span>
        {!isDir && node.size !== undefined && (
          <span className="text-xs text-muted-foreground ml-auto">
            {(node.size / 1024).toFixed(1)} KB
          </span>
        )}
      </div>
      {isDir && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedPaths={selectedPaths}
              expandedPaths={expandedPaths}
              onToggleSelect={onToggleSelect}
              onToggleExpand={onToggleExpand}
              onLoadChildren={onLoadChildren}
              loadingPaths={loadingPaths}
              isPathSelected={isPathSelected}
              isPathExcluded={isPathExcluded}
            />
          ))}
        </div>
      )}
    </div>
  );
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
  const [inputMode, setInputMode] = useState<"select" | "paste">("select");
  const [repositories, setRepositories] = useState<GitHubRepository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>(initialRepo);
  const [repoLink, setRepoLink] = useState<string>(initialRepo);
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [loadingPaths, setLoadingPaths] = useState<Set<string>>(new Set());
  const [treeRoot, setTreeRoot] = useState<FileNode | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(() => {
    // Initialize with both included paths and excluded paths (prefixed with !)
    const initial = new Set<string>(initialPaths);
    initialExcludePaths.forEach(path => initial.add(`!${path}`));
    return initial;
  });
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string>("");
  const [tokenEstimate, setTokenEstimate] = useState<number | null>(null);

  // Load tree on open if we have initial repo and paths
  useEffect(() => {
    if (open && initialRepo && initialPaths.length > 0 && !treeRoot) {
      loadTree();
    }
  }, [open]);

  // Load repositories when dialog opens
  useEffect(() => {
    if (open && inputMode === "select" && repositories.length === 0) {
      loadRepositories();
    }
  }, [open, inputMode]);

  const loadRepositories = async () => {
    try {
      setIsLoadingRepos(true);
      setError("");
      const response = await api.listGitHubRepositories();
      setRepositories(response.repositories);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repositories");
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const parseGitHubLink = (link: string): string | null => {
    try {
      // Handle various GitHub URL formats
      // https://github.com/owner/repo
      // https://github.com/owner/repo.git
      // git@github.com:owner/repo.git
      const match = link.match(/github\.com[:/]([^/]+\/[^/\s.]+)/);
      if (match) {
        return match[1].replace(/\.git$/, "");
      }
      // Also accept owner/repo format directly
      if (/^[^/]+\/[^/]+$/.test(link.trim())) {
        return link.trim();
      }
      return null;
    } catch {
      return null;
    }
  };

  const getRepoIdentifier = (): string => {
    if (inputMode === "select") {
      return selectedRepo;
    } else {
      const parsed = parseGitHubLink(repoLink);
      return parsed || "";
    }
  };

  const loadTree = async () => {
    const repo = getRepoIdentifier();
    if (!repo) {
      setError("Please select or enter a valid repository");
      return;
    }

    try {
      setIsLoadingTree(true);
      setError("");
      const tree = await api.browseGitHubTree(repo, "");
      setTreeRoot(tree);
      setExpandedPaths(new Set([tree.path]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repository tree");
      setTreeRoot(null);
    } finally {
      setIsLoadingTree(false);
    }
  };

  const loadChildren = async (path: string) => {
    const repo = getRepoIdentifier();
    if (!repo || !treeRoot) return;

    try {
      setLoadingPaths(prev => new Set(prev).add(path));
      const subtree = await api.browseGitHubTree(repo, path);
      
      // Update the tree with loaded children
      const updateNode = (node: FileNode): FileNode => {
        if (node.path === path) {
          return { ...node, children: subtree.children };
        }
        if (node.children) {
          return { ...node, children: node.children.map(updateNode) };
        }
        return node;
      };

      setTreeRoot(updateNode(treeRoot));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load directory");
    } finally {
      setLoadingPaths(prev => {
        const next = new Set(prev);
        next.delete(path);
        return next;
      });
    }
  };

  const toggleExpand = (path: string) => {
    setExpandedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const getAllFilesInDir = (node: FileNode): string[] => {
    if (node.type === "file") {
      return [node.path];
    }
    if (!node.children) {
      return [];
    }
    return node.children.flatMap(child => getAllFilesInDir(child));
  };

  const getAllPathsInDir = (node: FileNode): string[] => {
    const paths = [node.path];
    if (node.children) {
      node.children.forEach(child => {
        paths.push(...getAllPathsInDir(child));
      });
    }
    return paths;
  };

  const isPathSelected = (path: string): boolean => {
    // Check if this exact path is selected
    if (selectedPaths.has(path)) {
      return true;
    }
    
    // Empty path (root) should only be selected if explicitly in the set
    if (path === "") {
      return false;
    }
    
    // Check if root is selected (covers all paths)
    if (selectedPaths.has("")) {
      return true;
    }
    
    // Check if any parent directory is selected
    const pathParts = path.split('/');
    for (let i = 1; i < pathParts.length; i++) {
      const parentPath = pathParts.slice(0, i).join('/');
      if (selectedPaths.has(parentPath)) {
        return true;
      }
    }
    
    return false;
  };

  const isPathExcluded = (path: string): boolean => {
    return selectedPaths.has(`!${path}`);
  };

  const toggleSelect = (path: string, isDir: boolean) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      const isCurrentlySelected = isPathSelected(path);
      const isCurrentlyExcluded = isPathExcluded(path);
      
      if (isCurrentlySelected && !next.has(path)) {
        // Path is selected via parent, so exclude it
        next.add(`!${path}`);
      } else if (isCurrentlyExcluded) {
        // Remove exclusion
        next.delete(`!${path}`);
      } else if (next.has(path)) {
        // Deselect this path
        next.delete(path);
        
        // Also remove any exclusions under this path
        if (isDir && treeRoot) {
          const findNode = (node: FileNode): FileNode | null => {
            if (node.path === path) return node;
            if (node.children) {
              for (const child of node.children) {
                const found = findNode(child);
                if (found) return found;
              }
            }
            return null;
          };
          
          const dirNode = findNode(treeRoot);
          if (dirNode) {
            const allPaths = getAllPathsInDir(dirNode);
            allPaths.forEach(p => {
              next.delete(`!${p}`);
            });
          }
        }
      } else {
        // Select this path
        next.add(path);
        
        // Remove any exclusions under this path
        if (isDir && treeRoot) {
          const findNode = (node: FileNode): FileNode | null => {
            if (node.path === path) return node;
            if (node.children) {
              for (const child of node.children) {
                const found = findNode(child);
                if (found) return found;
              }
            }
            return null;
          };
          
          const dirNode = findNode(treeRoot);
          if (dirNode) {
            const allPaths = getAllPathsInDir(dirNode);
            allPaths.forEach(p => {
              next.delete(`!${p}`);
            });
          }
        }
      }
      
      return next;
    });
  };

  // Estimate tokens when selection changes
  useEffect(() => {
    const estimateTokens = async () => {
      const repo = getRepoIdentifier();
      if (!repo || selectedPaths.size === 0) {
        setTokenEstimate(null);
        return;
      }

      try {
        // Separate included and excluded paths
        const paths: string[] = [];
        const excludePaths: string[] = [];
        
        selectedPaths.forEach(path => {
          if (path.startsWith('!')) {
            excludePaths.push(path.substring(1));
          } else {
            paths.push(path);
          }
        });
        
        if (paths.length === 0) {
          setTokenEstimate(null);
          return;
        }
        
        console.log('Estimating tokens for:', { repo, paths, excludePaths });
        const estimate = await api.estimateGitHubTokens(repo, paths, excludePaths);
        console.log('Token estimate result:', estimate);
        setTokenEstimate(estimate.total_tokens);
      } catch (err) {
        console.error('Token estimation error:', err);
        // Silently fail token estimation
        setTokenEstimate(null);
      }
    };

    estimateTokens();
  }, [selectedPaths, inputMode, selectedRepo, repoLink]);

  const handleAddFiles = async () => {
    if (!chatId) {
      setError("No active chat selected");
      return;
    }

    const repo = getRepoIdentifier();
    if (!repo) {
      setError("Please select or enter a valid repository");
      return;
    }

    if (selectedPaths.size === 0) {
      setError("Please select at least one file");
      return;
    }

    // Separate included and excluded paths
    const paths: string[] = [];
    const excludePaths: string[] = [];
    
    selectedPaths.forEach(path => {
      if (path.startsWith('!')) {
        excludePaths.push(path.substring(1));
      } else {
        paths.push(path);
      }
    });

    if (paths.length === 0) {
      setError("Please select at least one file or folder");
      return;
    }

    try {
      setIsAdding(true);
      setError("");
      
      // First, clear any existing GitHub files from the backend
      // This ensures unchecked files are removed
      await api.removeGitHubFilesFromChat(chatId);
      
      // Then add the newly selected files
      const result = await api.addGitHubFilesToChat(chatId, repo, paths, excludePaths);
      
      // Success! Close dialog and notify parent with the selection details
      onFilesAdded?.(repo, paths, excludePaths, result.count);
      onOpenChange(false);
      
      // Don't reset state - keep it for re-opening
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add files");
    } finally {
      setIsAdding(false);
    }
  };

  const handleClose = () => {
    // Just close, don't reset state so user can re-open and modify
    setError("");
    onOpenChange(false);
  };

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
          {/* Repository Selection */}
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button
                variant={inputMode === "select" ? "default" : "outline"}
                size="sm"
                onClick={() => setInputMode("select")}
                className="flex-1"
              >
                Select from list
              </Button>
              <Button
                variant={inputMode === "paste" ? "default" : "outline"}
                size="sm"
                onClick={() => setInputMode("paste")}
                className="flex-1"
              >
                Paste GitHub link
              </Button>
            </div>

            {inputMode === "select" ? (
              <div className="space-y-2">
                <Label htmlFor="repository">Repository</Label>
                {isLoadingRepos ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin" />
                  </div>
                ) : (
                  <Select value={selectedRepo} onValueChange={setSelectedRepo}>
                    <SelectTrigger id="repository">
                      <SelectValue placeholder="Select a repository" />
                    </SelectTrigger>
                    <SelectContent>
                      {repositories.map((repo) => (
                        <SelectItem key={repo.id} value={repo.full_name}>
                          <div className="flex flex-col items-start">
                            <span className="font-medium">{repo.full_name}</span>
                            {repo.description && (
                              <span className="text-xs text-muted-foreground truncate max-w-[300px]">
                                {repo.description}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="repo-link">GitHub Repository Link</Label>
                <Input
                  id="repo-link"
                  placeholder="https://github.com/owner/repo or owner/repo"
                  value={repoLink}
                  onChange={(e) => setRepoLink(e.target.value)}
                />
              </div>
            )}

            <Button
              onClick={loadTree}
              disabled={isLoadingTree || !getRepoIdentifier()}
              className="w-full"
            >
              {isLoadingTree ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading repository...
                </>
              ) : (
                "Load Repository"
              )}
            </Button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
              {error}
            </div>
          )}

          {/* File Tree */}
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

          {/* Selection Summary */}
          {(() => {
            const includedCount = Array.from(selectedPaths).filter(p => !p.startsWith('!')).length;
            const excludedCount = Array.from(selectedPaths).filter(p => p.startsWith('!')).length;
            
            if (includedCount === 0) return null;
            
            return (
              <div className="flex items-center justify-between text-sm bg-muted p-3 rounded-md">
                <span>
                  <strong>{includedCount}</strong> item{includedCount !== 1 ? "s" : ""} selected
                  {excludedCount > 0 && ` (${excludedCount} excluded)`}
                </span>
                {tokenEstimate !== null && (
                  <span className="text-muted-foreground">
                    ~{tokenEstimate.toLocaleString()} tokens
                  </span>
                )}
              </div>
            );
          })()}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isAdding}>
            Cancel
          </Button>
          <Button
            onClick={handleAddFiles}
            disabled={isAdding || selectedPaths.size === 0 || !chatId}
          >
            {isAdding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Adding files...
              </>
            ) : (() => {
              const includedCount = Array.from(selectedPaths).filter(p => !p.startsWith('!')).length;
              return `Add ${includedCount} item${includedCount !== 1 ? "s" : ""}`;
            })()}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
