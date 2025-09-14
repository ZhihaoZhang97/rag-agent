import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useDocuments } from "@/providers/Documents";
import { Upload, X, Trash2, FileText, RefreshCw, FileType, BookOpen, File, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from "framer-motion";

const getFileIcon = (fileType: string) => {
  switch (fileType) {
    case 'pdf':
      return <FileType className="h-5 w-5 text-red-500" />;
    case 'md':
    case 'markdown':
      return <BookOpen className="h-5 w-5 text-blue-500" />;
    case 'txt':
      return <FileText className="h-5 w-5 text-gray-500" />;
    case 'docx':
    case 'doc':
      return <File className="h-5 w-5 text-blue-600" />;
    default:
      return <FileText className="h-5 w-5 text-gray-500" />;
  }
};

const UploadProgress = ({ progress }: { progress: number }) => {
  return (
    <div className="relative h-5 w-5">
      {/* Outer spinning ring */}
      <div className="absolute inset-0">
        <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      </div>
      {/* Progress circle background */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="h-4 w-4 rounded-full bg-blue-50 border border-blue-200">
          {/* Progress fill */}
          <div 
            className="h-full rounded-full bg-blue-500 transition-all duration-300 ease-out"
            style={{
              width: `${progress}%`,
              maxWidth: '100%'
            }}
          />
        </div>
      </div>
      {/* Progress text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[7px] font-bold text-white drop-shadow-sm">
          {Math.round(progress)}
        </span>
      </div>
    </div>
  );
};

export function DocumentSidebar() {
  const {
    documents,
    uploadingDocuments,
    isLoading,
    documentSidebarOpen,
    setDocumentSidebarOpen,
    uploadFile,
    deleteFile,
    refreshDocuments,
  } = useDocuments();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);

  const handleDeleteDocument = async (documentId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingDocumentId(documentId);
    try {
      await deleteFile(documentId);
    } finally {
      setDeletingDocumentId(null);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setIsUploading(true);
    try {
      // Process the first file
      await uploadFile(files[0]);
    } finally {
      setIsUploading(false);
      // Reset the file input
      e.target.value = "";
    }
  };

  return (
    <motion.div
      className="fixed right-0 top-0 z-50 h-full overflow-hidden border-l bg-white w-[350px] sm:w-[450px]"
      initial={{ x: "100%" }}
      animate={{ x: documentSidebarOpen ? 0 : "100%" }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      aria-hidden={!documentSidebarOpen}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-lg font-semibold">Document Library</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDocumentSidebarOpen(false)}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="flex flex-col space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Documents</h3>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refreshDocuments()}
                  disabled={isLoading}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading || isLoading || uploadingDocuments.length > 0}
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleFileChange}
                  accept=".pdf,.txt,.docx,.md"
                />
              </div>
            </div>

            <Separator />

            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center justify-between">
                    <Skeleton className="h-10 w-full" />
                  </div>
                ))}
              </div>
            ) : documents.length === 0 && uploadingDocuments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <FileText className="h-10 w-10 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No documents yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Upload documents to get started
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {/* Show uploading documents first */}
                {uploadingDocuments.map((uploadingDoc) => (
                  <motion.div
                    key={uploadingDoc.id}
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                    className="flex items-center justify-between rounded-md border p-2 bg-blue-50 border-blue-200"
                  >
                    <div className="flex items-center space-x-2">
                      <UploadProgress progress={uploadingDoc.progress} />
                      <div>
                        <p className="text-sm font-medium truncate max-w-[250px] text-blue-700">
                          {uploadingDoc.sanitizedName}
                        </p>
                        <p className="text-xs text-blue-500">
                          Uploading... {Math.round(uploadingDoc.progress)}%
                        </p>
                      </div>
                    </div>
                    <div className="text-xs text-blue-500 font-medium">
                      {uploadingDoc.progress < 100 ? 'Uploading' : 'Processing'}
                    </div>
                  </motion.div>
                ))}
                
                {/* Show existing documents */}
                {documents.map((doc) => {
                  const isDeleting = deletingDocumentId === doc.document_id;
                  const fileExtension = doc.filename.split('.').pop()?.toLowerCase() || '';
                  
                  return (
                    <div
                      key={doc.document_id}
                      className="flex items-center justify-between rounded-md border p-2"
                    >
                      <div className="flex items-center space-x-2">
                        {getFileIcon(fileExtension)}
                        <div>
                          <p className="text-sm font-medium truncate max-w-[250px]">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-gray-500">
                            {doc.chunks} chunks
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => handleDeleteDocument(doc.document_id, doc.filename, e)}
                        className="text-gray-500 hover:text-red-500"
                        disabled={isDeleting}
                        title={`Delete ${doc.filename}`}
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="border-t p-4">
          <p className="text-xs text-gray-500">
            Uploaded documents are processed and stored in the vector database for AI retrieval.
          </p>
        </div>
      </div>
    </motion.div>
  );
}
