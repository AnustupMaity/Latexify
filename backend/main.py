import os
import re
import requests
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

def build_prompt(req: GenerateRequest) -> str:
    return f"""
You are an expert LaTeX developer. Convert the following text into compilation-ready, high-quality LaTeX code.
DO NOT include surrounding markdown formatting like ```latex. Output ONLY the raw LaTeX code starting with \documentclass.

TEMPLATE TYPE: {req.template}
USER INSTRUCTIONS: {req.instructions}

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
    
    prompt = build_prompt(req)
    
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

def _run_ai_generation(prompt: str) -> str:
    """Helper to run the fallback AI chain."""
    if genai_client:
        try:
            res = genai_client.models.generate_content(model='gemini-2.5-pro', contents=prompt)
            return extract_latex(res.text)
        except Exception:
            try:
                res = genai_client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=prompt, 
                    config=types.GenerateContentConfig(temperature=0.2)
                )
                return extract_latex(res.text)
            except Exception:
                pass
    return extract_latex(call_huggingface_fallback(prompt))

def _save_to_supabase(req: GenerateRequest, latex_code: str, status: str):
    if not supabase: return
    try:
        # Simplistic title extraction from request
        title = req.input_text[:20].strip() + "..." if len(req.input_text) > 20 else "Untitled"
        data = {
            "title": title,
            "input_text": req.input_text,
            "instructions": req.instructions,
            "latex_code": latex_code,
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

@app.post("/api/generate-and-compile", response_model=GenerateCompileResponse)
def generate_and_compile(req: GenerateRequest):
    # 1. Initial Generation
    initial_prompt = build_prompt(req)
    try:
        current_latex = _run_ai_generation(initial_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initial AI generation failed: {str(e)}")

    max_retries = 3
    retries = 0

    while retries <= max_retries:
        # 2. Compile
        compile_res_model = compile_latex(CompileRequest(latex_code=current_latex))
        
        if compile_res_model.success:
            _save_to_supabase(req, current_latex, "success")
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

@app.post("/api/auth/logout", response_model=AuthResponse)
def logout():
    # Placeholder for session invalidation if using cookies/JWT
    return AuthResponse(success=True, message="Logged out successfully.")
