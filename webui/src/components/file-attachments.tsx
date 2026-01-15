import { File, Github, X } from "lucide-react";

interface FileAttachmentsProps {
  uploadedFiles: string[];
  githubFiles: { repo: string; paths: string[]; excludePaths: string[] };
  onRemoveFile: (filename: string) => void;
  onRemoveGitHubFiles: () => void;
  onEditGitHubFiles: () => void;
}

export function FileAttachments({
  uploadedFiles,
  githubFiles,
  onRemoveFile,
  onRemoveGitHubFiles,
  onEditGitHubFiles,
}: FileAttachmentsProps) {
  if (uploadedFiles.length === 0 && githubFiles.paths.length === 0) {
    return null;
  }

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {/* Uploaded files */}
      {uploadedFiles.map((filename, index) => (
        <div
          key={`${filename}-${index}`}
          className="flex items-center gap-1.5 rounded-md border border-border bg-primary/10 px-2 py-1 text-xs"
        >
          <File className="h-3.5 w-3.5 text-primary" />
          <span className="text-primary font-medium">{filename}</span>
          <button
            onClick={() => onRemoveFile(filename)}
            className="ml-1 hover:text-destructive transition-colors"
            aria-label={`Remove ${filename}`}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}

      {/* GitHub files */}
      {githubFiles.paths.length > 0 && (
        <div className="flex items-center gap-1.5 rounded-md border border-border bg-blue-500/10 px-2 py-1 text-xs">
          <Github className="h-3.5 w-3.5 text-blue-600" />
          <span className="text-blue-600 font-medium">
            {githubFiles.paths.length} item{githubFiles.paths.length !== 1 ? "s" : ""} from{" "}
            {githubFiles.repo.split("/")[1] || githubFiles.repo}
            {githubFiles.excludePaths.length > 0 && ` (${githubFiles.excludePaths.length} excluded)`}
          </span>
          <button
            onClick={onEditGitHubFiles}
            className="ml-1 hover:text-blue-700 transition-colors"
            aria-label="Edit GitHub files"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
          </button>
          <button
            onClick={onRemoveGitHubFiles}
            className="ml-1 hover:text-destructive transition-colors"
            aria-label="Remove GitHub files"
            title="Remove GitHub files"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
