import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useEffect,
  useCallback,
} from "react";
import { toast } from "sonner";
import { useQueryState, parseAsBoolean } from "nuqs";
import { 
  DocumentInfo, 
  uploadDocument, 
  listDocuments, 
  deleteDocument 
} from "@/lib/document-service";

interface DocumentsContextType {
  documents: DocumentInfo[];
  isLoading: boolean;
  documentSidebarOpen: boolean;
  setDocumentSidebarOpen: (open: boolean) => void;
  uploadFile: (file: File) => Promise<DocumentInfo | undefined>;
  deleteFile: (documentId: string) => Promise<boolean>;
  refreshDocuments: () => Promise<void>;
}

const DocumentsContext = createContext<DocumentsContextType | undefined>(undefined);

export const DocumentsProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [documentSidebarOpen, setDocumentSidebarOpen] = useQueryState(
    "documentSidebarOpen",
    parseAsBoolean.withDefault(false)
  );

  const refreshDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
      toast.error("Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load documents on initial render
  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const uploadFile = useCallback(async (file: File): Promise<DocumentInfo | undefined> => {
    setIsLoading(true);
    try {
      const result = await uploadDocument(file);
      // Refresh to ensure identifiers (document_id) match backend list (filename-based)
      await refreshDocuments();
      toast.success(`Document "${file.name}" uploaded successfully`);
      return result;
    } catch (error) {
      console.error("Error uploading document:", error);
      toast.error(
        `Failed to upload document: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
      return undefined;
    } finally {
      setIsLoading(false);
    }
  }, [refreshDocuments]);

  const deleteFile = useCallback(async (documentId: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((doc) => doc.document_id !== documentId));
      toast.success("Document deleted successfully");
      return true;
    } catch (error) {
      console.error("Error deleting document:", error);
      toast.error(
        `Failed to delete document: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <DocumentsContext.Provider
      value={{
        documents,
        isLoading,
        documentSidebarOpen,
        setDocumentSidebarOpen,
        uploadFile,
        deleteFile,
        refreshDocuments,
      }}
    >
      {children}
    </DocumentsContext.Provider>
  );
};

export const useDocuments = (): DocumentsContextType => {
  const context = useContext(DocumentsContext);
  if (context === undefined) {
    throw new Error("useDocuments must be used within a DocumentsProvider");
  }
  return context;
};

export default DocumentsContext;
