import { File, Link as LinkIcon, X } from "lucide-react";

interface FileAttachmentsProps {
  uploadedFiles: import('../lib/api').FileResource[];
  connectorFiles: { connector: string; paths: string[]; excludePaths: string[] };
  onRemoveFile: (fileId: string) => void;
  onRemoveConnectorFiles: () => void;
  onEditConnectorFiles: () => void;
}

export function FileAttachments({
  uploadedFiles,
  connectorFiles,
  onRemoveFile,
  onRemoveConnectorFiles,
  onEditConnectorFiles,
}: FileAttachmentsProps) {
  if ((!uploadedFiles || uploadedFiles.length === 0) && (!connectorFiles || !connectorFiles.paths || connectorFiles.paths.length === 0)) {
    return null;
  }

  const connectorLabel = connectorFiles.connector.includes('/') 
    ? (connectorFiles.connector.split("/")[1] || connectorFiles.connector)
    : connectorFiles.connector;

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {/* Uploaded files */}
      {(uploadedFiles || []).map((f, index) => (
        <div
          key={`${f.id}-${index}`}
          className="flex items-center gap-1.5 rounded-md border border-border bg-primary/10 px-2 py-1 text-xs"
        >
          <File className="h-3.5 w-3.5 text-primary" />
          <span className="text-primary font-medium">{f.filename}</span>
          <button
            onClick={() => onRemoveFile(f.id)}
            className="ml-1 hover:text-destructive transition-colors"
            aria-label={`Remove ${f.filename}`}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}

      {/* Connector files */}
      {connectorFiles.paths.length > 0 && (
        <div className="flex items-center gap-1.5 rounded-md border border-border bg-blue-500/10 px-2 py-1 text-xs">
          <LinkIcon className="h-3.5 w-3.5 text-blue-600" />
          <span className="text-blue-600 font-medium">
            {connectorFiles.paths.length} item{connectorFiles.paths.length !== 1 ? "s" : ""} from{" "}
            {connectorLabel}
            {connectorFiles.excludePaths.length > 0 && ` (${connectorFiles.excludePaths.length} excluded)`}
          </span>
          <button
            onClick={onEditConnectorFiles}
            className="ml-1 hover:text-blue-700 transition-colors"
            aria-label="Edit connector files"
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
            onClick={onRemoveConnectorFiles}
            className="ml-1 hover:text-destructive transition-colors"
            aria-label="Remove connector files"
            title="Remove connector files"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
