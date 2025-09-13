"use client";

import { Thread } from "@/components/thread";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";
import { DocumentsProvider } from "@/providers/Documents";
import { DocumentSidebar } from "@/components/document-sidebar";
import { ArtifactProvider } from "@/components/thread/artifact";
import { Toaster } from "@/components/ui/sonner";
import React from "react";

export default function DemoPage(): React.ReactNode {
  return (
    <React.Suspense fallback={<div>Loading (layout)...</div>}>
      <Toaster />
      <ThreadProvider>
        <StreamProvider>
          <DocumentsProvider>
            <ArtifactProvider>
              <Thread />
              <DocumentSidebar />
            </ArtifactProvider>
          </DocumentsProvider>
        </StreamProvider>
      </ThreadProvider>
    </React.Suspense>
  );
}
