"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Play, RotateCcw, Download, FileText, FileCode2, AlertCircle, Loader2, ImagePlus, X } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GenerationState = "idle" | "generating" | "success" | "error" | "loading_history";

export default function EditorPage() {
  const [title, setTitle] = useState("Untitled Document");
  const [inputText, setInputText] = useState("");
  const [instructions, setInstructions] = useState("");
  const [sources, setSources] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [state, setState] = useState<GenerationState>("idle");
  const [pdfBase64, setPdfBase64] = useState<string | null>(null);
  const [latexCode, setLatexCode] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [retries, setRetries] = useState(0);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);

  useEffect(() => {
    // Check if ID is in the URL to load a specific document
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const docId = params.get("id");
      if (docId) {
        setState("loading_history");
        fetch(`${API_BASE}/api/documents/${docId}`)
          .then((res) => res.json())
          .then((data) => {
            if (data && !data.detail) {
              setTitle(data.title || "Untitled Document");
              setInputText(data.input_text || "");
              setInstructions(data.instructions || "");
              setLatexCode(data.latex_code || "");
              if (data.pdf_base64) {
                setPdfBase64(data.pdf_base64);
                setState("success");
              } else if (data.latex_code && data.status === "success") {
                setShowSource(true);
                setState("success");
              } else {
                setState("error");
              }
            } else {
              setState("idle");
            }
          })
          .catch(() => {
            setState("idle");
          });
      }
    }
  }, []);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setImages(prev => [...prev, event.target!.result as string]);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleGenerate = async () => {
    if (!inputText.trim() && images.length === 0) return;
    setState("generating");
    setErrorMsg(null);
    setPdfBase64(null);
    setLatexCode(null);

    try {
      const res = await fetch(`${API_BASE}/api/generate-and-compile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_text: inputText,
          instructions: instructions,
          template: "standard",
          title: title,
          images: images.length > 0 ? images : undefined,
          sources: sources.trim() ? sources : undefined
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Generation failed.");
      }

      if (data.success) {
        setPdfBase64(data.pdf_base64);
        setLatexCode(data.final_latex);
        setRetries(data.retries ?? 0);
        setState("success");
      } else {
        setLatexCode(data.final_latex);
        setRetries(data.retries ?? 0);
        setErrorMsg(data.message || "Failed to compile the document.");
        setState("error");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Unknown error occurred.");
      setState("error");
    }
  };

  const handleDownloadPdf = () => {
    if (!pdfBase64) return;
    const link = document.createElement("a");
    link.href = `data:application/pdf;base64,${pdfBase64}`;
    link.download = `${title.replace(/\s+/g, '_') || 'latexify_document'}.pdf`;
    link.click();
  };

  const handleDownloadTex = () => {
    if (!latexCode) return;
    const blob = new Blob([latexCode], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${title.replace(/\s+/g, '_') || 'latexify_document'}.tex`;
    link.click();
  };

  const isGenerating = state === "generating";

  return (
    <div className="h-screen w-full bg-background flex flex-col overflow-hidden">
      {/* Top Navbar */}
      <header className="h-14 border-b border-border bg-card/50 backdrop-blur-md flex items-center justify-between px-4 z-10 shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-md hover:bg-secondary">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex flex-col">
            <div className="flex items-center">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="text-sm font-semibold bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1 -ml-1 text-foreground"
                style={{ width: `${Math.max(title.length + 1, 10)}ch` }}
                placeholder="Untitled Document"
              />
              <span className="text-sm font-semibold text-muted-foreground mr-1">.tex</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {state === "success" && retries > 0
                ? `✅ Compiled after ${retries} auto-fix${retries > 1 ? "es" : ""}`
                : state === "success"
                ? "✅ Compiled successfully"
                : state === "error"
                ? "❌ Compilation failed"
                : state === "generating"
                ? "⚙️ Self-healing loop running..."
                : "Draft Mode"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {state === "success" && (
            <>
              <button
                onClick={handleDownloadTex}
                className="flex items-center gap-2 bg-card/80 backdrop-blur text-foreground text-xs px-3 py-1.5 rounded-md border border-border hover:bg-secondary transition-colors"
              >
                <FileCode2 className="w-3.5 h-3.5" /> .tex
              </button>
              <button
                onClick={handleDownloadPdf}
                className="flex items-center gap-2 bg-card/80 backdrop-blur text-foreground text-xs px-3 py-1.5 rounded-md border border-border hover:bg-secondary transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> PDF
              </button>
            </>
          )}
          <button
            disabled={isGenerating || (!inputText.trim() && images.length === 0)}
            onClick={handleGenerate}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            {isGenerating ? "Compiling..." : "Generate PDF"}
          </button>
        </div>
      </header>

      {/* Main Split Screen */}
      <main className="flex-1 flex overflow-hidden">

        {/* LEFT PANEL: Input */}
        <div className="w-1/2 flex flex-col border-r border-border bg-background">
          <div className="p-4 border-b border-border flex items-center justify-between bg-card/30">
            <h2 className="text-sm font-medium flex items-center gap-2">
              <FileText className="w-4 h-4" /> Input Content
            </h2>
          </div>

          <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto hidden-scrollbar">
            {/* Input Text Area */}
            <div className="flex flex-col group min-h-[200px]">
              <label className="text-xs font-medium text-muted-foreground mb-2">Text / Markdown</label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Write your research abstract, equations, or assignment here..."
                className="w-full bg-card/20 border border-border/50 rounded-lg p-4 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-blue-500 transition-shadow focus:bg-card/40 min-h-[200px]"
              />
            </div>

            {/* Math/Image OCR Upload */}
            <div className="flex flex-col">
              <label className="text-xs font-medium text-muted-foreground mb-2">Math/Image OCR (Upload Screenshots)</label>
              <div className="w-full border-2 border-dashed border-border/50 rounded-lg p-4 flex flex-col items-center justify-center bg-card/10 hover:bg-card/30 transition-colors relative cursor-pointer">
                <input 
                  type="file" 
                  multiple 
                  accept="image/*" 
                  onChange={handleImageUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                  title="Upload images"
                />
                <ImagePlus className="w-6 h-6 text-muted-foreground mb-2" />
                <span className="text-xs text-muted-foreground">Click or Drag & Drop images here</span>
              </div>
              {images.length > 0 && (
                <div className="flex gap-2 mt-2 overflow-x-auto pb-2">
                  {images.map((img, i) => (
                    <div key={i} className="relative w-16 h-16 rounded-md overflow-hidden border border-border group shrink-0">
                      <img src={img} alt="upload preview" className="w-full h-full object-cover" />
                      <button 
                        onClick={() => removeImage(i)}
                        className="absolute top-0 right-0 bg-red-500/80 text-white p-0.5 rounded-bl hover:bg-red-500 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Bibliography Area */}
            <div className="flex flex-col">
              <label className="text-xs font-medium text-muted-foreground mb-2">Sources / Bibliography</label>
              <textarea
                value={sources}
                onChange={(e) => setSources(e.target.value)}
                placeholder="Paste URLs, DOIs, or raw citations here to generate a BibTeX automatically..."
                className="w-full bg-card/20 border border-border/50 rounded-lg p-4 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-blue-500 transition-shadow min-h-[100px]"
              />
            </div>

            {/* Instructions Panel */}
            <div className="flex flex-col">
              <label className="text-xs font-medium text-muted-foreground mb-2">AI Instructions</label>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="E.g., Format it as an IEEE research paper. Use the authblk package for authors..."
                className="w-full bg-blue-500/5 border border-blue-500/20 rounded-lg p-4 text-sm resize-y focus:outline-none focus:ring-1 focus:ring-blue-500 transition-shadow min-h-[100px]"
              />
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: PDF Preview */}
        <div className="w-1/2 bg-[#020817] relative flex flex-col">
          {/* Top bar */}
          <div className="p-4 flex items-center justify-between border-b border-border/30 bg-card/20 shrink-0">
            <div className="flex gap-2">
              <button
                onClick={() => setShowSource(false)}
                className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${!showSource ? "bg-blue-600 border-blue-600 text-white" : "border-border text-muted-foreground hover:bg-secondary"}`}
              >
                PDF Preview
              </button>
              <button
                onClick={() => setShowSource(true)}
                disabled={!latexCode}
                className={`text-xs px-3 py-1.5 rounded-md border transition-colors disabled:opacity-30 ${showSource ? "bg-blue-600 border-blue-600 text-white" : "border-border text-muted-foreground hover:bg-secondary"}`}
              >
                LaTeX Source
              </button>
            </div>
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !inputText.trim()}
              title="Regenerate"
              className="text-muted-foreground hover:text-foreground border border-border p-1.5 rounded-md transition-colors disabled:opacity-30"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

            {/* CONTENT AREA */}
            <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto hidden-scrollbar">
            {/* LOADING HISTORY */}
            {state === "loading_history" && (
              <div className="w-full max-w-2xl bg-white rounded flex-1 min-h-[600px] shadow-2xl flex flex-col items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
                <p className="text-sm text-gray-500">Loading document...</p>
              </div>
            )}

            {/* IDLE */}
            {state === "idle" && (
              <div className="w-full max-w-2xl bg-white rounded flex-1 min-h-[600px] shadow-2xl flex flex-col items-center justify-center text-gray-400">
                <FileText className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-sm font-medium">No PDF generated yet.</p>
                <p className="text-xs mt-1 opacity-60">Enter content on the left and click Generate PDF</p>
              </div>
            )}

            {/* GENERATING */}
            {state === "generating" && (
              <div className="w-full max-w-2xl bg-white rounded flex-1 min-h-[600px] shadow-2xl flex flex-col items-center justify-center gap-4">
                <div className="w-10 h-10 rounded-full border-4 border-blue-100 border-t-blue-500 animate-spin" />
                <div className="text-center">
                  <p className="text-sm font-semibold text-blue-600">Self-Healing Loop Active</p>
                  <p className="text-xs text-gray-400 mt-1">AI is generating → compiling → fixing errors...</p>
                </div>
              </div>
            )}

            {/* SUCCESS — PDF embed */}
            {state === "success" && !showSource && pdfBase64 && (
              <div className="w-full max-w-2xl flex-1 min-h-[600px] shadow-2xl rounded overflow-hidden">
                <iframe
                  src={`data:application/pdf;base64,${pdfBase64}`}
                  className="w-full h-full min-h-[600px]"
                  style={{ minHeight: "70vh" }}
                />
              </div>
            )}

            {/* SOURCE VIEW */}
            {showSource && latexCode && (
              <div className="w-full max-w-2xl flex-1 min-h-[600px] bg-[#0d1117] rounded border border-border/30 overflow-hidden">
                <pre className="p-4 text-xs text-green-400 font-mono whitespace-pre-wrap overflow-auto h-full" style={{ minHeight: "70vh" }}>
                  {latexCode}
                </pre>
              </div>
            )}

            {/* ERROR */}
            {state === "error" && (
              <div className="w-full max-w-2xl flex-1 min-h-[200px] flex flex-col items-center justify-center gap-4">
                <div className="flex items-center gap-3 text-red-400">
                  <AlertCircle className="w-6 h-6" />
                  <span className="font-semibold text-sm">Compilation Failed After {retries} Attempts</span>
                </div>
                <p className="text-xs text-muted-foreground text-center max-w-sm">{errorMsg}</p>
                {latexCode && (
                  <button
                    onClick={() => setShowSource(true)}
                    className="text-xs text-blue-400 hover:text-blue-300 underline"
                  >
                    View generated LaTeX source
                  </button>
                )}
                <button
                  onClick={handleGenerate}
                  className="mt-2 flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm transition-colors"
                >
                  <RotateCcw className="w-4 h-4" /> Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
