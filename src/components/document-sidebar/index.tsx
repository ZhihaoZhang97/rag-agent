import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useDocuments } from "@/providers/Documents";
import { Upload, X, Trash2, FileText, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { motion } from "framer-motion";

export function DocumentSidebar() {
  const {
    documents,
    isLoading,
    documentSidebarOpen,
    setDocumentSidebarOpen,
    uploadFile,
    deleteFile,
    refreshDocuments,
  } = useDocuments();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

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
                  disabled={isUploading || isLoading}
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleFileChange}
                  accept=".pdf,.txt,.docx"
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
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <FileText className="h-10 w-10 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No documents yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Upload documents to get started
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="flex items-center justify-between rounded-md border p-2"
                  >
                    <div className="flex items-center space-x-2">
                      <FileText className="h-5 w-5 text-blue-500" />
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
                      onClick={() => deleteFile(doc.document_id)}
                      className="text-gray-500 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span className="sr-only">Delete</span>
                    </Button>
                  </div>
                ))}
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
