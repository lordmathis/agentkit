import { Loader2 } from "lucide-react";
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
  onLoadTree: () => void;
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
  onLoadTree,
  getRepoIdentifier,
}: RepoSelectorProps) {
  return (
    <div className="space-y-3">
      <div className="flex gap-1 border border-border rounded-md p-0.5 bg-muted/50">
        <Button
          variant={inputMode === "select" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setInputMode("select")}
          className="flex-1 h-7 text-xs"
        >
          Select from list
        </Button>
        <Button
          variant={inputMode === "paste" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setInputMode("paste")}
          className="flex-1 h-7 text-xs"
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
        onClick={onLoadTree}
        disabled={isLoadingTree || !getRepoIdentifier()}
        variant="outline"
        size="sm"
        className="w-full h-8"
      >
        {isLoadingTree ? (
          <>
            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            Loading repository...
          </>
        ) : (
          "Load Repository"
        )}
      </Button>
    </div>
  );
}
