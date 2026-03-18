import { useState } from "react";
import { api, type FileResource } from "../lib/api";

export function useChatFiles(chatId: string | undefined) {
  const [uploadedFiles, setUploadedFiles] = useState<FileResource[]>([]);
  const [connectorFiles, setConnectorFilesState] = useState<{
    connectorId: string;
    resourceId: string;
    paths: string[];
    excludePaths: string[];
  }>({ connectorId: "", resourceId: "", paths: [], excludePaths: [] });
  const [isUploading, setIsUploading] = useState(false);
...
  const setConnectorFiles = (connectorId: string, resourceId: string, paths: string[], excludePaths: string[], files: FileResource[]) => {
    setConnectorFilesState({ connectorId, resourceId, paths, excludePaths });
    setUploadedFiles((prev) => [...prev, ...files]);
  };

  const removeConnectorFiles = async () => {
    setConnectorFilesState({ connectorId: "", resourceId: "", paths: [], excludePaths: [] });
  };

  const clearAll = () => {
    setUploadedFiles([]);
    setConnectorFilesState({ connectorId: "", resourceId: "", paths: [], excludePaths: [] });
  };

  const removeFile = async (id: string) => {
    try {
      await api.deleteFile(id);
      setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    } catch (error) {
      console.error("Failed to remove file:", error);
      setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
    }
  };

  const setConnectorFiles = (connector: string, paths: string[], excludePaths: string[], files: FileResource[]) => {
    setConnectorFilesState({ connector, paths, excludePaths });
    setUploadedFiles((prev) => [...prev, ...files]);
  };

  const removeConnectorFiles = async () => {
    setConnectorFilesState({ connector: "", paths: [], excludePaths: [] });
  };

  const clearAll = () => {
    setUploadedFiles([]);
    setConnectorFilesState({ connector: "", paths: [], excludePaths: [] });
  };

  return {
    uploadedFiles,
    connectorFiles,
    isUploading,
    uploadFiles,
    removeFile,
    setConnectorFiles,
    removeConnectorFiles,
    clearAll,
  };
}
