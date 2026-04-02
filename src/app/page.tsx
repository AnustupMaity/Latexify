import Link from "next/link";
import { ArrowRight, Sparkles, Wand2, FileText, Settings, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <div className="relative isolate overflow-hidden bg-background">
      {/* Background Gradients */}
      <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80">
        <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#3b82f6] to-[#93c5fd] opacity-20 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]" />
      </div>

      <div className="px-6 lg:px-8 max-w-7xl mx-auto py-24 sm:py-32 lg:py-40 relative">
        <div className="text-center animate-float">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 font-medium text-sm mb-8 ring-1 ring-blue-500/20">
            <Sparkles className="w-4 h-4" />
            <span>LaTeXify AI 1.0 is here</span>
          </div>
          <h1 className="text-5xl font-extrabold tracking-tight sm:text-7xl mb-8">
            Convert Text → <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500 text-glow">Perfect LaTeX</span> → PDF instantly
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground max-w-3xl mx-auto">
            The world's first self-healing AI LaTeX platform. Input your text, choose your style, and let AI generate, compile, and fix errors automatically until you have a perfect PDF.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Link
              href="/login"
              className="rounded-lg bg-blue-600 px-8 py-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-all hover:scale-105 active:scale-95 group flex items-center gap-2"
            >
              Get Started <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link href="#features" className="text-sm font-semibold leading-6 text-foreground hover:text-blue-400 transition-colors">
              Learn more <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>

        {/* Features Section */}
        <div id="features" className="mt-32 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="glass-panel p-8 rounded-2xl hover:border-blue-500/50 transition-colors group">
              <div className="bg-blue-500/20 w-12 h-12 rounded-lg flex items-center justify-center mb-6 text-blue-400 group-hover:scale-110 transition-transform">
                <Wand2 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">AI Generation</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Powered by Google Gemini, we convert your raw text and instructions directly into structured, professional LaTeX code.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="glass-panel p-8 rounded-2xl hover:border-indigo-500/50 transition-colors group">
              <div className="bg-indigo-500/20 w-12 h-12 rounded-lg flex items-center justify-center mb-6 text-indigo-400 group-hover:scale-110 transition-transform">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Fixes Errors Automatically</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Our self-healing compiler reads error logs and instructs the AI to fix them. Output is guaranteed to compile perfectly.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="glass-panel p-8 rounded-2xl hover:border-purple-500/50 transition-colors group">
              <div className="bg-purple-500/20 w-12 h-12 rounded-lg flex items-center justify-center mb-6 text-purple-400 group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3">Beautiful Templates</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Start from stunning presets including Resumes, IEEE Research Papers, Assignments, and Modern Beamer Slides.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
