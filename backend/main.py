import os
import re
import requests
import pypandoc
import concurrent.futures
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI(title="LaTeXify AI API")

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if origins:
        return origins
    frontend_url = os.getenv("FRONTEND_URL")
    defaults = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if frontend_url:
        defaults.append(frontend_url.strip())
    return defaults

# Configurable CORS for production and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_API_URL = os.getenv(
    "HUGGINGFACE_API_URL",
    "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct",
)

from supabase import create_client, Client

genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key")
security = HTTPBearer()

def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload.get("email")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

    # Keep the fallback configurable so Render/local environments can swap endpoints if needed.
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 2000, "return_full_text": False}
    }

    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise Exception(f"Hugging Face request failed: {exc}") from exc

    data = response.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"]
    if isinstance(data, dict) and data.get("generated_text"):
        return data["generated_text"]

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
    additional_files: dict[str, str | bytes] = {}

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
            file_path = os.path.join(temp_dir, filename)
            if isinstance(content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

        try:
            # First latex pass
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            # Bibliography passes if bib file exists
            if "references.bib" in req.additional_files:
                subprocess.run(
                    ["bibtex", "document"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=temp_dir
                )
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
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
                detail="LaTeX toolchain not found (pdflatex/bibtex). Make sure TeX Live is installed in the environment."
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
            mime_type = "image/jpeg"
            if "," in b64:
                header, body = b64.split(",", 1)
                b64 = body
                if ";" in header and ":" in header:
                    mime_type = header.split(":", 1)[1].split(";", 1)[0]
            try:
                img_bytes = base64.b64decode(b64)
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
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

def _save_to_supabase(req: GenerateRequest, latex_code: str, status: str, pdf_base64: str | None = None, user_email: str | None = None):
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
        if user_email:
            data["user_email"] = user_email
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

def _image_extension_from_mime(mime_type: str) -> str:
    mime_map = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "image/bmp": "bmp",
    }
    return mime_map.get(mime_type.lower(), "jpg")

def _materialize_uploaded_images(images: list[str] | None) -> tuple[dict[str, bytes], list[str]]:
    files: dict[str, bytes] = {}
    names: list[str] = []
    if not images:
        return files, names
    for idx, raw in enumerate(images, start=1):
        data = raw
        mime_type = "image/jpeg"
        if "," in raw:
            header, body = raw.split(",", 1)
            data = body
            if ";" in header and ":" in header:
                mime_type = header.split(":", 1)[1].split(";", 1)[0]
        try:
            decoded = base64.b64decode(data)
            ext = _image_extension_from_mime(mime_type)
            filename = f"uploaded_image_{idx}.{ext}"
            files[filename] = decoded
            names.append(filename)
        except Exception as e:
            print(f"Skipping invalid uploaded image #{idx}: {e}")
    return files, names

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

def _ensure_image_blocks(latex_code: str, image_names: list[str]) -> str:
    if not latex_code or not image_names:
        return latex_code

    updated = latex_code
    if "\\usepackage{graphicx}" not in updated and "\\documentclass" in updated:
        updated = re.sub(
            r"(\\documentclass[^\n]*\n)",
            r"\1\\usepackage{graphicx}\n",
            updated,
            count=1,
        )

    missing = [img for img in image_names if img not in updated]
    if not missing:
        return updated

    figure_blocks = "\n".join(
        [
            "\\begin{figure}[h!]\n\\centering\n"
            f"\\includegraphics[width=0.85\\linewidth]{{{img}}}\n"
            f"\\caption{{Uploaded image: {img}}}\n"
            "\\end{figure}"
            for img in missing
        ]
    )

    if "\\end{document}" in updated:
        updated = updated.replace("\\end{document}", figure_blocks + "\n\\end{document}")
    else:
        updated += "\n" + figure_blocks
    return updated

@app.post("/api/generate-and-compile", response_model=GenerateCompileResponse)
def generate_and_compile(req: GenerateRequest, user_email: str = Depends(get_current_user_email)):
    is_large = len(req.input_text) > 3000
    
    additional_files: dict[str, str | bytes] = {}
    image_files, image_names = _materialize_uploaded_images(req.images)
    additional_files.update(image_files)
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

        image_instruction = ""
        if image_names:
            image_instruction = (
                "\nAVAILABLE IMAGE FILES FOR LATEX \\includegraphics:\n"
                + "\n".join([f"- {n}" for n in image_names])
                + "\nIf relevant, include figures using these exact filenames."
            )
        initial_prompt = build_prompt(req, base_latex) + image_instruction
        try:
            current_latex = _run_ai_generation(initial_prompt, req.images)
            current_latex = _ensure_image_blocks(current_latex, image_names)
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

            # Preserve original chunk order for deterministic document assembly.
            chunk_results.sort(key=lambda x: int(x[0].split("_")[1].split(".")[0]))
            chunk_filenames: list[str] = []
            for filename, content in chunk_results:
                additional_files[filename] = content
                chunk_filenames.append(filename)
            current_latex = generate_main_tex(chunk_filenames, req)
            current_latex = _ensure_image_blocks(current_latex, image_names)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chunked parallel generation failed: {str(e)}")

    max_retries = 3
    retries = 0

    while retries <= max_retries:
        # 2. Compile
        compile_res_model = compile_latex(CompileRequest(latex_code=current_latex, additional_files=additional_files))
        
        if compile_res_model.success:
            _save_to_supabase(req, current_latex, "success", compile_res_model.pdf_base64, user_email)
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
                current_latex = _ensure_image_blocks(current_latex, image_names)
            except Exception as e:
                _save_to_supabase(req, current_latex, "error", None, user_email)
                return GenerateCompileResponse(
                    success=False,
                    final_latex=current_latex,
                    retries=retries,
                    message=f"AI failed during error correction: {str(e)}"
                )
        
        retries += 1

    _save_to_supabase(req, current_latex, "error", None, user_email)
    # If all retries exhausted and still failed
    return GenerateCompileResponse(
        success=False,
        final_latex=current_latex,
        retries=max_retries,
        message="Failed to compile after maximum automatic error fixes. Please review the LaTeX code manually."
    )

import random

# In-memory OTP fallback store (email -> {code, exp})
OTP_STORE = {}
OTP_EXPIRY_MINUTES = 10

class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    token: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "example@gmail.com")

@app.post("/api/auth/send-otp", response_model=AuthResponse)
def send_otp(req: SendOtpRequest):
    if not BREVO_API_KEY:
        raise HTTPException(status_code=500, detail="BREVO_API_KEY is not configured in backend.")
    
    # Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    normalized_email = req.email.lower().strip()
    expiry_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)
    stored_in_db = False
    if supabase:
        try:
            supabase.table("otp_codes").upsert(
                {
                    "email": normalized_email,
                    "otp_code": otp_code,
                    "expires_at": expiry_at.isoformat(),
                    "created_at": datetime.datetime.utcnow().isoformat(),
                },
                on_conflict="email",
            ).execute()
            stored_in_db = True
        except Exception as e:
            print(f"OTP db upsert failed, using memory fallback: {e}")
    if not stored_in_db:
        OTP_STORE[normalized_email] = {
            "code": otp_code,
            "exp": expiry_at,
        }
    
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
    normalized_email = req.email.lower().strip()
    now_utc = datetime.datetime.utcnow()
    matched = False
    if supabase:
        try:
            db_resp = (
                supabase.table("otp_codes")
                .select("email, otp_code, expires_at")
                .eq("email", normalized_email)
                .limit(1)
                .execute()
            )
            row = db_resp.data[0] if db_resp.data else None
            if row:
                expires_at_raw = row.get("expires_at")
                expires_at = None
                if isinstance(expires_at_raw, str):
                    expires_at = datetime.datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                if expires_at and now_utc > expires_at:
                    raise HTTPException(status_code=400, detail="Verification code expired.")
                matched = row.get("otp_code") == req.token
                if matched:
                    supabase.table("otp_codes").delete().eq("email", normalized_email).execute()
        except HTTPException:
            raise
        except Exception as e:
            print(f"OTP db read failed, trying memory fallback: {e}")
    if not matched:
        mem_row = OTP_STORE.get(normalized_email)
        if mem_row:
            if now_utc > mem_row["exp"]:
                del OTP_STORE[normalized_email]
                raise HTTPException(status_code=400, detail="Verification code expired.")
            matched = mem_row["code"] == req.token
            if matched:
                del OTP_STORE[normalized_email]

    if matched:
        # Create JWT token valid for 7 days
        token = jwt.encode(
            {"email": normalized_email, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
            JWT_SECRET,
            algorithm="HS256"
        )
        return AuthResponse(success=True, message="OTP verified successfully.", token=token)
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code or no OTP requested.")

@app.get("/api/documents")
def get_documents(limit: int = 10, user_email: str = Depends(get_current_user_email)):
    if not supabase:
        return []   # Supabase not configured — return empty instead of crashing
    try:
        response = supabase.table("Documents").select("id, title, status, created_at").eq("user_email", user_email).order("id", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        err = str(e)
        # If table doesn't exist yet or user_email column missing, try fallback
        if "PGRST205" in err or "does not exist" in err or "schema cache" in err or "user_email" in err:
            try:
                response = supabase.table("documents").select("id, title, status, created_at").eq("user_email", user_email).order("id", desc=True).limit(limit).execute()
                return response.data
            except Exception as e2:
                print("Warning: Documents table not found or missing user_email column.", e2)
                return []
        raise HTTPException(status_code=500, detail=err)

@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int, user_email: str = Depends(get_current_user_email)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.table("Documents").select("*").eq("id", doc_id).eq("user_email", user_email).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        return response.data[0]
    except Exception as e:
        err = str(e)
        if "relation" in err or "does not exist" in err or "schema cache" in err or "user_email" in err:
            try:
                response = supabase.table("documents").select("*").eq("id", doc_id).eq("user_email", user_email).execute()
                if not response.data:
                    raise HTTPException(status_code=404, detail="Document not found")
                return response.data[0]
            except Exception as e2:
                raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=err)

@app.post("/api/auth/logout", response_model=AuthResponse)
def logout():
    # Placeholder for session invalidation if using cookies/JWT
    return AuthResponse(success=True, message="Logged out successfully.")
