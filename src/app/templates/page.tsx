import Link from "next/link";
import { FileText, Clock, LayoutTemplate, Plus } from "lucide-react";

export default function TemplatesPage() {
  const templates = [
    { title: "IEEE Research Paper", category: "Academic", description: "Standard double-column IEEE format for conferences and journals." },
    { title: "Modern Resume", category: "Professional", description: "Clean, ATS-friendly resume template with dynamic sections." },
    { title: "University Assignment", category: "Academic", description: "Simple layout with title page and equation formatting." },
    { title: "Beamer Presentation", category: "Slides", description: "Professional slide deck for academic presentations." },
  ];

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
            <Link href="/templates" className="flex items-center gap-3 px-3 py-2 bg-secondary text-foreground rounded-lg text-sm font-medium transition-colors">
              <LayoutTemplate className="w-4 h-4 text-muted-foreground" /> Templates
            </Link>
            <Link href="/history" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:bg-secondary/50 rounded-lg text-sm font-medium transition-colors">
              <FileText className="w-4 h-4" /> All History
            </Link>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <header className="h-14 flex items-center px-8 border-b border-border shrink-0">
          <h1 className="text-lg font-semibold text-foreground">Document Templates</h1>
        </header>

        <div className="flex-1 p-8 overflow-y-auto hidden-scrollbar">
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((tpl, i) => (
              <Link href={`/editor?template=${tpl.title.toLowerCase().replace(/ /g, "_")}`} key={i} className="glass-panel p-6 rounded-2xl flex flex-col hover:border-blue-500/50 transition-colors group cursor-pointer aspect-[4/3] relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-start justify-between mb-auto z-10">
                   <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center">
                     <LayoutTemplate className="w-5 h-5 text-muted-foreground group-hover:text-blue-400 transition-colors" />
                   </div>
                   <span className="text-xs font-semibold px-2 py-1 bg-secondary rounded-md text-muted-foreground">
                     {tpl.category}
                   </span>
                </div>
                <div className="z-10 mt-4">
                  <h3 className="font-semibold text-foreground mb-2 text-lg group-hover:text-blue-400 transition-colors">{tpl.title}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">{tpl.description}</p>
                </div>
              </Link>
            ))}
          </div>

        </div>
      </main>
    </div>
  );
}
