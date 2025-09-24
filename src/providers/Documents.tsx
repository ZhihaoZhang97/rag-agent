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
import { v4 as uuidv4 } from "uuid";
import {
  DocumentInfo,
  uploadDocument,
  listDocuments,
  deleteDocument
} from "@/lib/document-service";

interface UploadingDocument {
  id: string;
  originalName: string;
  sanitizedName: string;
  progress: number;
  fileType: string;
}

interface DocumentsContextType {
  documents: DocumentInfo[];
  uploadingDocuments: UploadingDocument[];
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
  const [uploadingDocuments, setUploadingDocuments] = useState<UploadingDocument[]>([]);
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

  const sanitizeFilename = (filename: string): string => {
    return filename.replace(/\s+/g, '_');
  };

  const getFileExtension = (filename: string): string => {
    return filename.split('.').pop()?.toLowerCase() || '';
  };

  const uploadFile = useCallback(async (file: File): Promise<DocumentInfo | undefined> => {
    const uploadId = uuidv4();
    const sanitizedName = sanitizeFilename(file.name);
    const fileType = getFileExtension(file.name);
    
    // Add to uploading list with initial progress
    const uploadingDoc: UploadingDocument = {
      id: uploadId,
      originalName: file.name,
      sanitizedName,
      progress: 0,
      fileType
    };
    
    setUploadingDocuments(prev => [...prev, uploadingDoc]);
    
    // Small delay to ensure UI renders before starting progress
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Start with initial progress update to ensure animation is visible
    setUploadingDocuments(prev => 
      prev.map(doc => 
        doc.id === uploadId 
          ? { ...doc, progress: 5 }
          : doc
      )
    );
    
    // Simulate gradual progress updates
    const progressInterval = setInterval(() => {
      setUploadingDocuments(prev => 
        prev.map(doc => {
          if (doc.id === uploadId) {
            const increment = Math.random() * 8 + 2; // Random between 2-10
            const newProgress = Math.min(doc.progress + increment, 85);
            return { ...doc, progress: newProgress };
          }
          return doc;
        })
      );
    }, 300); // Slightly slower for better visibility

    try {
      const result = await uploadDocument(file);
      
      // Complete progress smoothly
      setUploadingDocuments(prev => 
        prev.map(doc => 
          doc.id === uploadId 
            ? { ...doc, progress: 100 }
            : doc
        )
      );
      
      // Remove from uploading list after a brief delay to show completion
      setTimeout(() => {
        setUploadingDocuments(prev => prev.filter(doc => doc.id !== uploadId));
      }, 800);
      
      // Refresh to ensure identifiers (document_id) match backend list (filename-based)
      await refreshDocuments();
      toast.success(`Document "${sanitizedName}" uploaded successfully`);
      return result;
    } catch (error) {
      console.error("Error uploading document:", error);
      toast.error(
        `Failed to upload document: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
      // Remove from uploading list on error
      setUploadingDocuments(prev => prev.filter(doc => doc.id !== uploadId));
      return undefined;
    } finally {
      clearInterval(progressInterval);
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
        uploadingDocuments,
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
