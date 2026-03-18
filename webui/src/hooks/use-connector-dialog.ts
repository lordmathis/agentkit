import { useState, useEffect } from "react";
import { api, type ConnectorResource, type FileNode, type Connector } from "../lib/api";

export function useConnectorDialog(
  initialInstance: string,
  initialConnector: string,
  initialPaths: string[],
  initialExcludePaths: string[]
) {
  const [inputMode, setInputMode] = useState<"select" | "paste">("select");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [selectedConnector, setSelectedConnector] = useState<string>(initialInstance);
  const [isLoadingConnectors, setIsLoadingConnectors] = useState(false);
  const [resources, setResources] = useState<ConnectorResource[]>([]);
  const [selectedResource, setSelectedResource] = useState<string>(initialConnector);
  const [resourceLink, setResourceLink] = useState<string>(initialConnector);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
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
  const [isEstimatingTokens, setIsEstimatingTokens] = useState(false);

  const parseConnectorLink = (link: string): string | null => {
    try {
      // GitHub specific parsing logic (remains but renamed for generic use)
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

  const getResourceIdentifier = (): string => {
    if (inputMode === "select") {
      return selectedResource;
    } else {
      const parsed = parseConnectorLink(resourceLink);
      return parsed || "";
    }
  };

  const loadConnectors = async () => {
    try {
      setIsLoadingConnectors(true);
      setError("");
      const response = await api.listConnectors();
      setConnectors(response.connectors);
      if (response.connectors.length > 0 && !selectedConnector) {
        setSelectedConnector(response.connectors[0].name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connectors");
    } finally {
      setIsLoadingConnectors(false);
    }
  };

  const loadResources = async () => {
    if (!selectedConnector) return;
    try {
      setIsLoadingResources(true);
      setError("");
      const response = await api.listConnectorResources(selectedConnector);
      setResources(response.resources);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resources");
    } finally {
      setIsLoadingResources(false);
    }
  };

  const loadTree = async () => {
    const resource = getResourceIdentifier();
    if (!resource) {
      setError("Please select or enter a valid resource");
      return;
    }

    try {
      setIsLoadingTree(true);
      setError("");
      const tree = await api.browseConnectorTree(selectedConnector, resource, "");
      setTreeRoot(tree);
      setExpandedPaths(new Set([tree.path]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resource tree");
      setTreeRoot(null);
    } finally {
      setIsLoadingTree(false);
    }
  };

  const loadChildren = async (path: string) => {
    const resource = getResourceIdentifier();
    if (!resource || !treeRoot || !selectedConnector) return;

    try {
      setLoadingPaths((prev) => new Set(prev).add(path));
      const subtree = await api.browseConnectorTree(selectedConnector, resource, path);

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

  const handleAddFiles = async (chatId: string | undefined, onSuccess: (resource: string, paths: string[], excludePaths: string[], files: import('../lib/api').FileResource[]) => void): Promise<import('../lib/api').FileResource[] | false> => {
    if (!chatId) {
      setError("No active chat selected");
      return false;
    }

    const resource = getResourceIdentifier();
    if (!resource) {
      setError("Please select or enter a valid resource");
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

      const fileResources = await api.uploadConnectorFiles(selectedConnector, resource, paths, excludePaths);
      onSuccess(resource, paths, excludePaths, fileResources);
      return fileResources;
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
      const resource = getResourceIdentifier();
      if (!resource || selectedPaths.size === 0 || !selectedConnector) {
        setTokenEstimate(null);
        setIsEstimatingTokens(false);
        return;
      }

      try {
        setIsEstimatingTokens(true);
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
          setIsEstimatingTokens(false);
          return;
        }

        const estimate = await api.estimateConnectorTokens(selectedConnector, resource, paths, excludePaths);
        setTokenEstimate(estimate.total_tokens);
      } catch (err) {
        console.error("Token estimation error:", err);
        setTokenEstimate(null);
      } finally {
        setIsEstimatingTokens(false);
      }
    };

    estimateTokens();
  }, [selectedPaths, inputMode, selectedResource, resourceLink, selectedConnector]);

  const handleResourceSelect = async (resource: string) => {
    setSelectedResource(resource);
    setInputMode("select");
    
    try {
      setIsLoadingTree(true);
      setError("");
      const tree = await api.browseConnectorTree(selectedConnector, resource, "");
      setTreeRoot(tree);
      setExpandedPaths(new Set([tree.path]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resource tree");
      setTreeRoot(null);
    } finally {
      setIsLoadingTree(false);
    }
  };

  const handleLinkPaste = async (link: string) => {
    const parsed = parseConnectorLink(link);
    if (!parsed) {
      setError("Invalid resource link");
      return;
    }
    
    setResourceLink(link);
    
    try {
      setIsLoadingTree(true);
      setError("");
      const tree = await api.browseConnectorTree(selectedConnector, parsed, "");
      setTreeRoot(tree);
      setExpandedPaths(new Set([tree.path]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resource tree");
      setTreeRoot(null);
    } finally {
      setIsLoadingTree(false);
    }
  };

  // Load connectors on mount
  useEffect(() => {
    loadConnectors();
  }, []);

  // Load resources when connector changes
  useEffect(() => {
    if (selectedConnector) {
      loadResources();
    }
  }, [selectedConnector]);

  return {
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
    setError,
    tokenEstimate,
    isEstimatingTokens,
    getResourceIdentifier,
    loadConnectors,
    loadResources,
    loadTree,
    loadChildren,
    toggleExpand,
    isPathSelected,
    isPathExcluded,
    toggleSelect,
    handleAddFiles,
    handleResourceSelect,
    handleLinkPaste,
  };
}
