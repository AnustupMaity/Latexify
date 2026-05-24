import os
import re
import requests
import pypandoc
import concurrent.futures
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI(title="LaTeXify AI API")

# Allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

from supabase import create_client, Client

genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
class GenerateRequest(BaseModel):
    input_text: str
    instructions: str = ""
    template: str = "standard"
    title: str | None = None
    images: list[str] | None = None
    sources: str | None = None

class GenerateResponse(BaseModel):
    latex: str
    model_used: str
    message: str = "Success"

def extract_latex(text: str) -> str:
    """Extracts raw LaTeX from a markdown response containing ```latex or ```tex."""
    match = re.search(r"```(?:latex|tex)(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()

def build_prompt(req: GenerateRequest, base_latex: str = None) -> str:
    template_instruction = ""
    t_lower = req.template.lower()
    if "ieee" in t_lower:
        template_instruction = "IMPORTANT: Use \\documentclass[conference]{IEEEtran}. Include standard packages like graphicx, amsmath. Do NOT use standard article."
    elif "resume" in t_lower:
        template_instruction = "IMPORTANT: Use a modern resume layout, for example \\documentclass[11pt,a4paper,sans]{moderncv} with \\moderncvstyle{classic} and \\moderncvcolor{blue}, OR a clean article-based resume. Include appropriate sections."
    elif "beamer" in t_lower or "presentation" in t_lower:
        template_instruction = "IMPORTANT: Use \\documentclass{beamer} and wrap content in \\begin{frame} ... \\end{frame} blocks."
    
    if base_latex:
        return f"""
You are an expert LaTeX developer. I have structurally converted the user's content into safe baseline LaTeX.
Your job is to apply the exact document constraints/styles below while retaining the underlying structure.
DO NOT break equations or lists. Output ONLY the raw LaTeX code starting with \\documentclass. DO NOT include markdown code fences (```latex).

TEMPLATE TYPE: {req.template}
{template_instruction}
USER INSTRUCTIONS: {req.instructions}
SOURCES/CITATIONS: {req.sources or 'None'}

If sources are provided, ensure you include \\bibliographystyle{{plainnat}} or similar and \\bibliography{{references}} before \\end{{document}}, and cite them appropriately (e.g. \\cite{{...}}) in the text if specified.

BASE LATEX STRUCTURE (Enhance this according to instructions):
{base_latex}
"""
    else:
        return f"""
You are an expert LaTeX developer. Convert the following text into compilation-ready, high-quality LaTeX code.
DO NOT include surrounding markdown formatting like ```latex. Output ONLY the raw LaTeX code starting with \\documentclass.

TEMPLATE TYPE: {req.template}
{template_instruction}
USER INSTRUCTIONS: {req.instructions}
SOURCES/CITATIONS: {req.sources or 'None'}

If sources are provided, ensure you include \\bibliographystyle{{plainnat}} or similar and \\bibliography{{references}} before \\end{{document}}, and cite them appropriately (e.g. \\cite{{...}}) in the text if specified.

TEXT CONTENT:
{req.input_text}
"""

def call_huggingface_fallback(prompt: str) -> str:
    """Fallback generator using HuggingFace Inference API (free)."""
    if not HUGGINGFACE_API_KEY or HUGGINGFACE_API_KEY == "your_hugging_face_key_here":
        raise Exception("Hugging Face API Key is missing.")
    
    # Using a capable open-source specific model suited for coding or general tasks
    API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 2000, "return_full_text": False}
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        raise Exception(f"HF Error {response.status_code}: {response.text}")

@app.post("/api/generate", response_model=GenerateResponse)
def generate_latex(req: GenerateRequest):
    if not genai_client:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured.")
    
    try:
        base_latex = pypandoc.convert_text(req.input_text, 'latex', format='md')
    except Exception as e:
        print("Pandoc conversion failed, falling back to raw text:", e)
        base_latex = None

    prompt = build_prompt(req, base_latex)
    
    # 1. Try Gemini 2.5 Pro
    try:
        response = genai_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
        )
        return GenerateResponse(
            latex=extract_latex(response.text),
            model_used="gemini-2.5-pro"
        )
    except Exception as e_pro:
        print(f"Gemini 2.5 Pro failed: {e_pro}")
        
        # 2. Try Gemini 2.5 Flash
        try:
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                )
            )
            return GenerateResponse(
                latex=extract_latex(response.text),
                model_used="gemini-2.5-flash",
                message="Our primary model (2.5 Pro) failed, operating on fallback (2.5 Flash)."
            )
        except Exception as e_flash:
            print(f"Gemini 2.5 Flash failed: {e_flash}")
            
            # 3. Try Hugging Face Fallback
            try:
                hf_output = call_huggingface_fallback(prompt)
                return GenerateResponse(
                    latex=extract_latex(hf_output),
                    model_used="huggingface-llama3",
                    message="Google Gemini systems are currently failing, operating on secondary open-source fallback."
                )
            except Exception as e_hf:
                print(f"Hugging Face fallback failed: {e_hf}")
                raise HTTPException(
                    status_code=500, 
                    detail="All AI generators failed. Please check your system or try again later."
                )

import subprocess
import tempfile
import base64

class CompileRequest(BaseModel):
    latex_code: str
    additional_files: dict[str, str] = {}

class CompileResponse(BaseModel):
    success: bool
    pdf_base64: str | None = None
    log_output: str | None = None
    message: str

@app.post("/api/compile", response_model=CompileResponse)
def compile_latex(req: CompileRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        tex_file_path = os.path.join(temp_dir, 'document.tex')
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(req.latex_code)
            
        for filename, content in req.additional_files.items():
            with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)

        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            pdf_path = os.path.join(temp_dir, 'document.pdf')
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as pdf_file:
                    encoded_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
                return CompileResponse(success=True, pdf_base64=encoded_pdf, message="Compilation successful")
            else:
                # Get the log for debugging
                log_path = os.path.join(temp_dir, 'document.log')
                log_content = result.stdout + result.stderr
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                        log_content = lf.read()
                return CompileResponse(
                    success=False,
                    log_output=log_content,
                    message="Compilation failed. See log output."
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="pdflatex not found. Make sure TeX Live is installed in the environment."
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Compilation timed out after 60 seconds.")

class GenerateCompileResponse(BaseModel):
    success: bool
    final_latex: str | None = None
    pdf_base64: str | None = None
    retries: int = 0
    message: str

def _run_ai_generation(prompt: str, images: list[str] | None = None) -> str:
    """Helper to run the fallback AI chain."""
    contents = [prompt]
    if images:
        for b64 in images:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(b64)
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            except Exception as e:
                print(f"Failed to decode image: {e}")

    if genai_client:
        try:
            res = genai_client.models.generate_content(model='gemini-2.5-pro', contents=contents)
            return extract_latex(res.text)
        except Exception as e:
            print(f"Pro fail: {e}")
            try:
                res = genai_client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=contents, 
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                return extract_latex(res.text)
            except Exception as e:
                print(f"Flash fail: {e}")
                pass
    return extract_latex(call_huggingface_fallback(prompt))

def _save_to_supabase(req: GenerateRequest, latex_code: str, status: str, pdf_base64: str | None = None):
    if not supabase: return
    try:
        # Simplistic title extraction from request, or use provided title
        title = req.title.strip() if req.title and req.title.strip() else (req.input_text[:20].strip() + "..." if len(req.input_text) > 20 else "Untitled Document")
        data = {
            "title": title,
            "input_text": req.input_text,
            "instructions": req.instructions,
            "latex_code": latex_code,
            "pdf_base64": pdf_base64,
            "status": status
        }
        supabase.table("Documents").insert(data).execute()
    except Exception as e:
        err = str(e)
        if "relation" in err or "does not exist" in err or "PGRST205" in err or "schema cache" in err:
            try:
                supabase.table("documents").insert(data).execute()
            except Exception as e2:
                print(f"Failed to save to Supabase fallback table 'documents': {e2}")
        else:
            print(f"Failed to save to Supabase: {e}")

def split_markdown_by_headings(text: str) -> list[tuple[str, str]]:
    chunks = []
    current_chunk = []
    chunk_index = 0
    # simple split by markdown header 1 or 2
    for line in text.split('\n'):
        if (line.startswith('# ') or line.startswith('## ')) and len(current_chunk) > 10:
            chunks.append((f"chunk_{chunk_index}.tex", "\n".join(current_chunk)))
            chunk_index += 1
            current_chunk = []
        current_chunk.append(line)
    if current_chunk:
        chunks.append((f"chunk_{chunk_index}.tex", "\n".join(current_chunk)))
    return chunks

def _generate_bibtex(sources: str) -> str:
    prompt = f"""
You are an expert academic librarian. I will provide a list of URLs, DOIs, or raw text references.
Convert them into valid BibTeX entries. Make sure to generate appropriate citation keys.
Output ONLY the raw BibTeX format (NO markdown formatting like ```bibtex).

SOURCES:
{sources}
"""
    if genai_client:
        try:
            res = genai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            # Remove any markdown if it leaked
            match = re.search(r"```(?:bibtex|bib)(.*?)```", res.text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else res.text.strip()
        except:
            pass
    return ""

def generate_chunk(chunk_tuple: tuple[str, str], req: GenerateRequest) -> tuple[str, str]:
    filename, content = chunk_tuple
    try:
        base_latex = pypandoc.convert_text(content, 'latex', format='md')
    except Exception:
        base_latex = None

    prompt = f"""
You are an expert LaTeX developer. Convert the following text into compilation-ready LaTeX.
This is a SECTION of a larger document. DO NOT output \\documentclass or \\begin{{document}}. Only the body LaTeX.
Output ONLY the raw LaTeX content, no markdown code delimiters (```latex).

TEMPLATE TYPE: {req.template}
USER INSTRUCTIONS: {req.instructions}

BASE LATEX STRUCTURE:
{base_latex if base_latex else content}
"""
    return filename, _run_ai_generation(prompt)

def generate_main_tex(chunk_filenames: list[str], req: GenerateRequest) -> str:
    prompt = f"""
You are an expert LaTeX developer. Generate a main.tex file for a document containing the following included files:
{', '.join(chunk_filenames)}

Use \\input{{filename}} to include them in the correct order.
Provide ONLY the raw LaTeX content starting with \\documentclass, NO markdown formatting, NO actual text content inside the document body (only the inputs).

TEMPLATE TYPE: {req.template}
USER INSTRUCTIONS: {req.instructions}
TITLE: {req.title or 'Untitled Document'}
"""
    return _run_ai_generation(prompt)

@app.post("/api/generate-and-compile", response_model=GenerateCompileResponse)
def generate_and_compile(req: GenerateRequest):
    is_large = len(req.input_text) > 3000
    
    additional_files = {}
    if req.sources:
        try:
            bibtex_content = _generate_bibtex(req.sources)
            if bibtex_content:
                additional_files["references.bib"] = bibtex_content
        except Exception as e:
            print(f"Bibtex generation failed: {e}")

    if not is_large:
        # 0. Pandoc structural pass
        # Normal flow
        try:
            base_latex = pypandoc.convert_text(req.input_text, 'latex', format='md')
        except Exception as e:
            print("Pandoc conversion failed, falling back to raw text:", e)
            base_latex = None

        initial_prompt = build_prompt(req, base_latex)
        try:
            current_latex = _run_ai_generation(initial_prompt, req.images)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Initial AI generation failed: {str(e)}")
    else:
        # CHUNKING FLOW
        try:
            chunks = split_markdown_by_headings(req.input_text)
            print(f"Splitting huge text into {len(chunks)} chunks.")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(generate_chunk, c, req) for c in chunks]
                chunk_results = [f.result() for f in concurrent.futures.as_completed(futures)]
                
            for filename, content in chunk_results:
                additional_files[filename] = content
            current_latex = generate_main_tex(list(additional_files.keys()), req)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chunked parallel generation failed: {str(e)}")

    max_retries = 3
    retries = 0

    while retries <= max_retries:
        # 2. Compile
        compile_res_model = compile_latex(CompileRequest(latex_code=current_latex, additional_files=additional_files))
        
        if compile_res_model.success:
            _save_to_supabase(req, current_latex, "success", compile_res_model.pdf_base64)
            return GenerateCompileResponse(
                success=True,
                final_latex=current_latex,
                pdf_base64=compile_res_model.pdf_base64,
                retries=retries,
                message="Successfully generated and compiled PDF."
            )
        
        # If we failed and still have retries left
        if retries < max_retries:
            fix_prompt = f"""
You are an expert LaTeX developer. The following LaTeX code failed to compile.
Here is the error log from pdflatex:
{compile_res_model.log_output}

Here is the failing LaTeX code:
{current_latex}

Fix the errors so it compiles properly. Output ONLY the corrected raw LaTeX code starting with \\documentclass. DO NOT include formatting like ```latex.
"""
            try:
                current_latex = _run_ai_generation(fix_prompt)
            except Exception as e:
                _save_to_supabase(req, current_latex, "error")
                return GenerateCompileResponse(
                    success=False,
                    final_latex=current_latex,
                    retries=retries,
                    message=f"AI failed during error correction: {str(e)}"
                )
        
        retries += 1

    _save_to_supabase(req, current_latex, "error")
    # If all retries exhausted and still failed
    return GenerateCompileResponse(
        success=False,
        final_latex=current_latex,
        retries=max_retries,
        message="Failed to compile after maximum automatic error fixes. Please review the LaTeX code manually."
    )

import random

# Simple in-memory OTP store for MVP (email -> string code)
OTP_STORE = {}

class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    token: str

class AuthResponse(BaseModel):
    success: bool
    message: str

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "example@gmail.com")

@app.post("/api/auth/send-otp", response_model=AuthResponse)
def send_otp(req: SendOtpRequest):
    if not BREVO_API_KEY:
        raise HTTPException(status_code=500, detail="BREVO_API_KEY is not configured in backend.")
    
    # Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    OTP_STORE[req.email] = otp_code
    
    # Call Brevo REST API
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    # Note: Sender email typically needs to be authorized in Brevo.
    payload = {
        "sender": {"name": "LaTeXify AI", "email": BREVO_SENDER_EMAIL},
        "to": [{"email": req.email}],
        "subject": "Your LaTeXify Login Code",
        "htmlContent": f"<html><body><h2>Welcome to LaTeXify!</h2><p>Your 6-digit verification code is: <strong>{otp_code}</strong></p></body></html>"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Brevo API Payload Sender: {BREVO_SENDER_EMAIL}")
    print(f"Brevo API Status: {response.status_code}")
    print(f"Brevo API Response: {response.text}")
    
    if response.status_code in [200, 201, 202]:
        return AuthResponse(success=True, message="OTP sent directly via Brevo.")
    else:
        # If it fails, usually because sender is unauthorized. Add message parsing.
        raise HTTPException(status_code=400, detail=f"Brevo API Error: {response.text}")

@app.post("/api/auth/verify-otp", response_model=AuthResponse)
def verify_otp(req: VerifyOtpRequest):
    stored_otp = OTP_STORE.get(req.email)
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="No OTP requested for this email.")
        
    if stored_otp == req.token:
        # Clear the token after use
        del OTP_STORE[req.email]
        return AuthResponse(success=True, message="OTP verified successfully.")
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

@app.get("/api/documents")
def get_documents(limit: int = 10):
    if not supabase:
        return []   # Supabase not configured — return empty instead of crashing
    try:
        response = supabase.table("Documents").select("id, title, status, created_at").order("id", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        err = str(e)
        # If table doesn't exist yet, return empty gracefully
        if "PGRST205" in err or "does not exist" in err or "schema cache" in err:
            try:
                response = supabase.table("documents").select("id, title, status, created_at").order("id", desc=True).limit(limit).execute()
                return response.data
            except Exception as e2:
                print("Warning: Documents/documents table not found. Run the SQL migration in Supabase Dashboard.")
                return []
        raise HTTPException(status_code=500, detail=err)

@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.table("Documents").select("*").eq("id", doc_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        return response.data[0]
    except Exception as e:
        err = str(e)
        if "relation" in err or "does not exist" in err or "schema cache" in err:
            try:
                response = supabase.table("documents").select("*").eq("id", doc_id).execute()
                if not response.data:
                    raise HTTPException(status_code=404, detail="Document not found")
                return response.data[0]
            except Exception:
                raise HTTPException(status_code=404, detail="Document not found / Table missing")
        raise HTTPException(status_code=500, detail=err)

@app.post("/api/auth/logout", response_model=AuthResponse)
def logout():
    # Placeholder for session invalidation if using cookies/JWT
    return AuthResponse(success=True, message="Logged out successfully.")
