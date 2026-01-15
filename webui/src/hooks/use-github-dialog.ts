import { useState, useEffect } from "react";
import { api, type GitHubRepository, type FileNode } from "../lib/api";

export function useGitHubDialog(
  initialRepo: string,
  initialPaths: string[],
  initialExcludePaths: string[]
) {
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
    const initial = new Set<string>(initialPaths);
    initialExcludePaths.forEach((path) => initial.add(`!${path}`));
    return initial;
  });
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string>("");
  const [tokenEstimate, setTokenEstimate] = useState<number | null>(null);

  const parseGitHubLink = (link: string): string | null => {
    try {
      const match = link.match(/github\.com[:/]([^/]+\/[^/\s.]+)/);
      if (match) {
        return match[1].replace(/\.git$/, "");
      }
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
      setLoadingPaths((prev) => new Set(prev).add(path));
      const subtree = await api.browseGitHubTree(repo, path);

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
      setLoadingPaths((prev) => {
        const next = new Set(prev);
        next.delete(path);
        return next;
      });
    }
  };

  const toggleExpand = (path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const getAllPathsInDir = (node: FileNode): string[] => {
    const paths = [node.path];
    if (node.children) {
      node.children.forEach((child) => {
        paths.push(...getAllPathsInDir(child));
      });
    }
    return paths;
  };

  const isPathSelected = (path: string): boolean => {
    if (selectedPaths.has(path)) {
      return true;
    }

    if (path === "") {
      return false;
    }

    if (selectedPaths.has("")) {
      return true;
    }

    const pathParts = path.split("/");
    for (let i = 1; i < pathParts.length; i++) {
      const parentPath = pathParts.slice(0, i).join("/");
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
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      const isCurrentlySelected = isPathSelected(path);
      const isCurrentlyExcluded = isPathExcluded(path);

      if (isCurrentlySelected && !next.has(path)) {
        next.add(`!${path}`);
      } else if (isCurrentlyExcluded) {
        next.delete(`!${path}`);
      } else if (next.has(path)) {
        next.delete(path);

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
            allPaths.forEach((p) => {
              next.delete(`!${p}`);
            });
          }
        }
      } else {
        next.add(path);

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
            allPaths.forEach((p) => {
              next.delete(`!${p}`);
            });
          }
        }
      }

      return next;
    });
  };

  const handleAddFiles = async (chatId: string | undefined, onSuccess: (repo: string, paths: string[], excludePaths: string[], count: number) => void) => {
    if (!chatId) {
      setError("No active chat selected");
      return false;
    }

    const repo = getRepoIdentifier();
    if (!repo) {
      setError("Please select or enter a valid repository");
      return false;
    }

    if (selectedPaths.size === 0) {
      setError("Please select at least one file");
      return false;
    }

    const paths: string[] = [];
    const excludePaths: string[] = [];

    selectedPaths.forEach((path) => {
      if (path.startsWith("!")) {
        excludePaths.push(path.substring(1));
      } else {
        paths.push(path);
      }
    });

    if (paths.length === 0) {
      setError("Please select at least one file or folder");
      return false;
    }

    try {
      setIsAdding(true);
      setError("");

      await api.removeGitHubFilesFromChat(chatId);
      const result = await api.addGitHubFilesToChat(chatId, repo, paths, excludePaths);

      onSuccess(repo, paths, excludePaths, result.count);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add files");
      return false;
    } finally {
      setIsAdding(false);
    }
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
        const paths: string[] = [];
        const excludePaths: string[] = [];

        selectedPaths.forEach((path) => {
          if (path.startsWith("!")) {
            excludePaths.push(path.substring(1));
          } else {
            paths.push(path);
          }
        });

        if (paths.length === 0) {
          setTokenEstimate(null);
          return;
        }

        const estimate = await api.estimateGitHubTokens(repo, paths, excludePaths);
        setTokenEstimate(estimate.total_tokens);
      } catch (err) {
        console.error("Token estimation error:", err);
        setTokenEstimate(null);
      }
    };

    estimateTokens();
  }, [selectedPaths, inputMode, selectedRepo, repoLink]);

  return {
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
  };
}
