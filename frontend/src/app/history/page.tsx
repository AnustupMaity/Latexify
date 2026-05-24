"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Clock, LayoutTemplate, Plus, Search, Filter } from "lucide-react";
import API_BASE from "@/lib/api";
import { clearSessionAndRedirect, isTokenExpired } from "@/lib/auth";

type DocItem = {
  id: number;
  title?: string;
  status?: string;
  created_at?: string;
};

export default function HistoryPage() {
  const [documents, setDocuments] = useState<DocItem[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token || isTokenExpired(token)) {
      clearSessionAndRedirect();
      return;
    }
    fetch(`${API_BASE}/api/documents?limit=50`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
      .then((res) => {
        if (res.status === 401) {
          clearSessionAndRedirect();
          return [];
        }
        return res.ok ? res.json() : [];
      })
      .then((data) => setDocuments(Array.isArray(data) ? data : []))
      .catch((error) => console.error("Failed to fetch documents:", error));
  }, []);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Sidebar - Copied for MVP */}
      <aside className="w-64 border-r border-border bg-card/30 flex flex-col hidden sm:flex shrink-0">
        <div className="h-14 flex items-center px-6 border-b border-border">
          <span className="font-bold text-lg text-foreground tracking-tight">LaTeXify AI</span>
        </div>
        
        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          <Link href="/editor" className="flex items-center gap-3 px-3 py-2 bg-blue-600/10 text-blue-500 rounded-lg text-sm font-medium transition-colors hover:bg-blue-600/20">
            <Plus className="w-4 h-4" /> New Document
          </Link>
          
          <div className="mt-6 space-y-1">
            <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:bg-secondary/50 rounded-lg text-sm font-medium transition-colors">
              <Clock className="w-4 h-4" /> Recent
            </Link>
            <Link href="/templates" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:bg-secondary/50 rounded-lg text-sm font-medium transition-colors">
              <LayoutTemplate className="w-4 h-4" /> Templates
            </Link>
            <Link href="/history" className="flex items-center gap-3 px-3 py-2 bg-secondary text-foreground rounded-lg text-sm font-medium transition-colors">
              <FileText className="w-4 h-4 text-muted-foreground" /> All History
            </Link>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <header className="h-14 flex items-center px-8 border-b border-border shrink-0">
          <h1 className="text-lg font-semibold text-foreground">Document History</h1>
        </header>

        <div className="flex-1 p-8 overflow-y-auto hidden-scrollbar">
          
          {/* Controls */}
          <div className="flex items-center gap-4 mb-8">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input 
                type="text"
                placeholder="Search documents..."
                className="w-full bg-input border border-border rounded-lg py-2 pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-secondary transition-colors">
              <Filter className="w-4 h-4" /> Filter
            </button>
          </div>

          <div className="flex flex-col gap-2">
            {documents.length > 0 ? documents.map((doc: any) => (
              <div key={doc.id} className="flex items-center justify-between p-4 bg-card/20 hover:bg-card/40 border border-border/50 rounded-xl transition-colors cursor-pointer group">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg text-muted-foreground group-hover:text-blue-400 transition-colors ${doc.status === 'success' ? 'bg-blue-500/10' : 'bg-secondary'}`}>
                      <FileText className={`w-5 h-5 ${doc.status === 'success' ? 'text-blue-400' : ''}`} />
                    </div>
                    <div>
                      <h3 className="font-medium text-foreground text-sm group-hover:text-blue-400 transition-colors">
                        {doc.title || `Document #${doc.id}`}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Generated on {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                     <span className={`text-xs px-2 py-1 rounded-md font-medium ${doc.status === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'}`}>
                       {doc.status === 'success' ? 'Success' : 'Failed'}
                     </span>
                     <Link href={`/editor?id=${doc.id}`} className="text-xs font-medium text-blue-500 hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                        Open
                     </Link>
                  </div>
                </div>
            )) : (
              <div className="p-12 text-center text-muted-foreground bg-card/10 rounded-xl border border-border/50 flex flex-col items-center">
                <FileText className="w-10 h-10 mb-4 opacity-20" />
                <p className="text-base text-foreground mb-1">No History Found</p>
                <p className="text-sm">You haven't generated any documents yet.</p>
                <Link href="/editor" className="text-blue-400 hover:text-blue-300 text-sm mt-4 transition-colors">Start creating →</Link>
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
