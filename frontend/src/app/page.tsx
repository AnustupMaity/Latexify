import Link from "next/link";
import { ArrowRight, Sparkles, Code2, FileText, Settings, ShieldAlert, Cpu } from "lucide-react";

export default function Home() {
  return (
    <div className="relative min-h-screen bg-background text-foreground overflow-hidden selection:bg-primary selection:text-white">
      {/* Dot pattern background */}
      <div className="absolute inset-0 z-0 bg-dot-pattern opacity-40 pointer-events-none mix-blend-screen" />
      
      {/* Vignette effect to darken edges */}
      <div className="absolute inset-0 z-0 bg-gradient-to-b from-transparent via-background/50 to-background pointer-events-none" />

      <div className="px-6 lg:px-8 max-w-7xl mx-auto py-24 sm:py-32 lg:py-40 relative z-10 flex flex-col items-center justify-center min-h-[90vh]">
        <div className="w-full max-w-4xl mx-auto">
          
          {/* Badge */}
          <div className="flex justify-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 border border-primary/40 bg-black/50 text-primary font-dot text-xs tracking-widest backdrop-blur-md">
              <Sparkles className="w-3.5 h-3.5" />
              <span>LATEXIFY OS [v1.0]</span>
            </div>
          </div>

          {/* Typography */}
          <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-center leading-[0.9] uppercase mb-8">
            Raw Text In. <br />
            <span className="text-primary italic pr-2">Perfect</span> LaTeX Out.
          </h1>
          
          <p className="mt-8 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto text-center font-medium">
            The self-healing AI compiler. Input natural text, and let the system generate, compile, and automatically fix errors until a flawless PDF is produced.
          </p>

          {/* Action Buttons */}
          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-4 bg-white text-black text-sm font-dot tracking-widest hover:bg-gray-200 transition-colors flex items-center justify-center gap-3 border border-white"
            >
              INITIALIZE SYSTEM <ArrowRight className="w-4 h-4" />
            </Link>
            <Link 
              href="#features" 
              className="w-full sm:w-auto px-8 py-4 bg-transparent text-white text-sm font-dot tracking-widest hover:bg-white/5 transition-colors flex items-center justify-center gap-2 border border-border"
            >
              VIEW SPECS
            </Link>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div id="features" className="relative z-10 border-t border-border bg-background">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border">
            
            {/* Feature 1 */}
            <div className="p-10 lg:p-16 group hover:bg-white/[0.02] transition-colors">
              <div className="mb-8 p-4 border border-border inline-block bg-black">
                <Cpu className="w-6 h-6 text-foreground group-hover:text-primary transition-colors" />
              </div>
              <h3 className="text-xl font-bold font-dot mb-4 uppercase">AI Code Gen</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Powered by Gemini models to convert unstructured text and complex instructions directly into strictly formatted LaTeX syntax.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-10 lg:p-16 group hover:bg-white/[0.02] transition-colors">
              <div className="mb-8 p-4 border border-border inline-block bg-black">
                <ShieldAlert className="w-6 h-6 text-foreground group-hover:text-primary transition-colors" />
              </div>
              <h3 className="text-xl font-bold font-dot mb-4 uppercase">Auto-Healing</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                The compiler intercepts fatal errors and automatically prompts the AI to resolve syntax mistakes until a valid PDF compiles.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-10 lg:p-16 group hover:bg-white/[0.02] transition-colors">
              <div className="mb-8 p-4 border border-border inline-block bg-black">
                <Code2 className="w-6 h-6 text-foreground group-hover:text-primary transition-colors" />
              </div>
              <h3 className="text-xl font-bold font-dot mb-4 uppercase">Strict Templates</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Start from robust configurations designed for IEEE Papers, academic Resumes, University Assignments, and modern presentations.
              </p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
