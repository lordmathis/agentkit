import { Loader2, Link as LinkIcon } from "lucide-react";
import { Label } from "../ui/label";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Input } from "../ui/input";
import { type GitHubRepository } from "../../lib/api";

interface RepoSelectorProps {
  inputMode: "select" | "paste";
  setInputMode: (mode: "select" | "paste") => void;
  selectedRepo: string;
  setSelectedRepo: (repo: string) => void;
  repoLink: string;
  setRepoLink: (link: string) => void;
  repositories: GitHubRepository[];
  isLoadingRepos: boolean;
  isLoadingTree: boolean;
  onRepoSelect: (repo: string) => void;
  onLinkPaste: (link: string) => void;
  getRepoIdentifier: () => string;
}

export function RepoSelector({
  inputMode,
  setInputMode,
  selectedRepo,
  setSelectedRepo,
  repoLink,
  setRepoLink,
  repositories,
  isLoadingRepos,
  isLoadingTree,
  onRepoSelect,
  onLinkPaste,
  getRepoIdentifier,
}: RepoSelectorProps) {
  const handleRepoChange = (repo: string) => {
    setSelectedRepo(repo);
    onRepoSelect(repo);
  };

  const handleLinkKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && repoLink.trim()) {
      onLinkPaste(repoLink);
    }
  };

  return (
    <div className="space-y-2">
      {inputMode === "select" ? (
        <div className="space-y-2">
          <Label htmlFor="repository">Repository</Label>
          <div className="flex gap-2 items-center">
            {isLoadingRepos ? (
              <div className="flex-1 flex items-center justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              <Select value={selectedRepo} onValueChange={handleRepoChange}>
                <SelectTrigger id="repository" className="flex-1">
                  <SelectValue placeholder="Select a repository" />
                </SelectTrigger>
                <SelectContent>
                  {repositories.map((repo) => (
                    <SelectItem key={repo.id} value={repo.full_name}>
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{repo.full_name}</span>
                        {repo.description && (
                          <span className="text-xs opacity-70 truncate max-w-[300px]">
                            {repo.description}
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9"
              onClick={() => setInputMode("paste")}
              title="Paste GitHub link"
            >
              <LinkIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor="repo-link">GitHub Repository Link</Label>
          <Input
            id="repo-link"
            placeholder="https://github.com/owner/repo or owner/repo"
            value={repoLink}
            onChange={(e) => setRepoLink(e.target.value)}
            onKeyDown={handleLinkKeyDown}
            autoFocus
          />
        </div>
      )}
      {isLoadingTree && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading repository...
        </div>
      )}
    </div>
  );
}
