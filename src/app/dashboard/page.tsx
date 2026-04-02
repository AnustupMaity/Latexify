import Link from "next/link";
import { FileText, Clock, LayoutTemplate, Plus } from "lucide-react";
import LogoutButton from "./LogoutButton";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let documents: any[] = [];
  try {
    const res = await fetch("http://localhost:8000/api/documents", { cache: "no-store" });
    if (res.ok) {
      documents = await res.json();
    }
  } catch (error) {
    console.error("Failed to fetch documents:", error);
  }

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card/30 flex flex-col hidden sm:flex shrink-0">
        <div className="h-14 flex items-center px-6 border-b border-border">
          <span className="font-bold text-lg text-foreground tracking-tight">LaTeXify AI</span>
        </div>
        
        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          <Link href="/editor" className="flex items-center gap-3 px-3 py-2 bg-blue-600/10 text-blue-500 rounded-lg text-sm font-medium transition-colors hover:bg-blue-600/20">
            <Plus className="w-4 h-4" /> New Document
          </Link>
          
          <div className="mt-6 space-y-1">
            <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 bg-secondary text-foreground rounded-lg text-sm font-medium">
              <Clock className="w-4 h-4 text-muted-foreground" /> Recent
            </Link>
            <Link href="/templates" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:bg-secondary/50 rounded-lg text-sm font-medium transition-colors">
              <LayoutTemplate className="w-4 h-4" /> Templates
            </Link>
            <Link href="/history" className="flex items-center gap-3 px-3 py-2 text-muted-foreground hover:bg-secondary/50 rounded-lg text-sm font-medium transition-colors">
              <FileText className="w-4 h-4" /> All History
            </Link>
          </div>
        </nav>

        <div className="p-4 border-t border-border mt-auto">
          <LogoutButton />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <div className="absolute top-1/4 right-1/4 w-[30rem] h-[30rem] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
        
        <header className="h-14 flex items-center px-8 border-b border-border shrink-0">
          <h1 className="text-lg font-semibold text-foreground">Dashboard</h1>
        </header>

        <div className="flex-1 p-8 overflow-y-auto hidden-scrollbar">
          
          {/* Quick Create Section */}
          <section className="mb-12">
            <h2 className="text-sm font-medium text-muted-foreground mb-4">Quick Create</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-4">
              <Link href="/editor" className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center text-center hover:border-blue-500/50 transition-colors group cursor-pointer aspect-video">
                <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center mb-3 group-hover:bg-blue-500/20 transition-colors">
                  <Plus className="w-5 h-5 text-blue-400 group-hover:scale-110 transition-transform" />
                </div>
                <span className="font-medium text-foreground">Blank Document</span>
              </Link>

              <Link href="/editor?template=ieee" className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center text-center hover:border-indigo-500/50 transition-colors group cursor-pointer aspect-video relative overflow-hidden">
                <div className="w-10 h-10 rounded-full bg-indigo-500/10 flex items-center justify-center mb-3 group-hover:bg-indigo-500/20 transition-colors">
                  <FileText className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
                </div>
                <span className="font-medium text-foreground">IEEE Paper</span>
              </Link>
            </div>
          </section>

          {/* Recent Documents Section */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-muted-foreground">Recent Documents</h2>
              <Link href="/history" className="text-sm font-medium text-blue-400 hover:text-blue-300">View all</Link>
            </div>
            
            <div className="grid grid-cols-1 gap-2">
              {documents.length > 0 ? documents.map((doc: any) => (
                <div key={doc.id} className="flex items-center justify-between p-4 bg-card/20 hover:bg-card/40 border border-border/50 rounded-xl transition-colors cursor-pointer group">
                  <div className="flex items-center gap-4">
                    <div className="bg-secondary p-2 rounded-lg text-muted-foreground flex shrink-0 items-center justify-center">
                      <FileText className="w-5 h-5 text-blue-400" />
                    </div>
                    <div className="min-w-0 flex-1 pr-4">
                      <h3 className="font-medium text-foreground text-sm group-hover:text-blue-400 transition-colors truncate">
                        {doc.title || `Document #${doc.id}`}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Generated on {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className={`text-xs px-2 py-1 rounded-md shrink-0 font-medium ${doc.status === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'}`}>
                    {doc.status === 'success' ? 'Success' : 'Failed'}
                  </div>
                </div>
              )) : (
                <div className="p-8 text-center text-muted-foreground bg-card/10 rounded-xl border border-border/50 flex flex-col items-center justify-center">
                  <FileText className="w-8 h-8 mb-3 opacity-20" />
                  <p className="text-sm">You haven't generated any documents yet.</p>
                  <Link href="/editor" className="text-blue-400 hover:text-blue-300 text-sm mt-2 transition-colors">Create your first LaTeX document →</Link>
                </div>
              )}
            </div>
          </section>

        </div>
      </main>
    </div>
  );
}
