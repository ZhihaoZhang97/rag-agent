import React from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { FileText } from "lucide-react";
import { useDocuments } from "@/providers/Documents";

export function DocumentSidebarToggle() {
  const { documentSidebarOpen, setDocumentSidebarOpen } = useDocuments();

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            onClick={() => setDocumentSidebarOpen(!documentSidebarOpen)}
          >
            <FileText className="h-5 w-5" />
            <span className="sr-only">Toggle document sidebar</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p>Document Library</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
