# LaTeXify AI

<p align="center">
  <a href="https://latexify-mu.vercel.app/">
    <img src="https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel" />
  </a>
  <a href="https://latexify-mu.vercel.app/">
    <img src="https://img.shields.io/badge/Open-App-00C853?style=for-the-badge" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI-Powered-blueviolet?style=flat-square" />
  <img src="https://img.shields.io/badge/LaTeX-Automation-success?style=flat-square" />
  <img src="https://img.shields.io/badge/PDF-Generation-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Production-Ready-black?style=flat-square" />
</p>

---

## 🚀 Live Demo

🔗 https://latexify-mu.vercel.app/

---
## Live Deployment

- Frontend (Vercel): `https://latexify-mu.vercel.app`
- Backend (Render): `https://latexify-backend.onrender.com`

## What It Does

- Converts raw text/markdown into high-quality LaTeX
- Compiles LaTeX into PDF on the backend
- Auto-retries/fixes LaTeX when compilation fails
- Supports references and BibTeX generation
- Supports image-assisted generation and LaTeX figure inclusion
- Stores generation history per user

## Architecture

### Frontend

- Next.js (App Router), React, Tailwind CSS
- OTP login flow
- Editor with:
  - text input
  - image upload
  - sources/bibliography input
  - PDF preview + `.tex` source view

### Backend

- FastAPI + Uvicorn
- Multi-model generation fallback:
  1. Gemini 2.5 Pro
  2. Gemini 2.5 Flash
  3. Hugging Face fallback model
- Native LaTeX compile pipeline (`pdflatex`, `bibtex`)
- Pandoc structural pass before AI formatting

### Database

- Supabase PostgreSQL
- Stores documents/history and OTP records
- Row Level Security (RLS) enabled and hardened

##  Generation Pipeline

### 1) Pandoc structural normalization

Input markdown/text is first converted with Pandoc (`pypandoc`) to generate a safer baseline LaTeX structure.  
This improves consistency before AI styling/transformation.

### 2) AI generation with template constraints

AI receives:
- baseline structure
- template choice (IEEE/resume/beamer/standard)
- user instructions
- optional source context
- optional image context

### 3) Image handling that compiles

Uploaded base64 images are now materialized as real files in the compile workspace (for example `uploaded_image_1.png`), so LaTeX `\includegraphics{...}` references are actually resolvable during compilation.

### 4) Large-document chunking

For large inputs:
- content is split by markdown headings
- chunks are generated in parallel
- chunk output order is normalized before assembly
- final `main.tex` is created using deterministic chunk ordering

### 5) Bibliography flow

If sources are provided:
- backend generates `references.bib`
- compile flow runs:
  1. `pdflatex`
  2. `bibtex`
  3. `pdflatex`
  4. `pdflatex`

This resolves references reliably in the output PDF.

### 6) Self-healing compile loop

If compile fails, log output is fed back to AI for correction and retry (up to configured attempts).

## Security and Data Controls

- JWT-based authentication for protected APIs
- User-scoped document reads/writes
- Supabase RLS enabled
- Broad table grants revoked for `anon`/`authenticated`
- Service-role-only access policies for backend-managed tables
- CORS allowlist is environment-driven (`CORS_ORIGINS`)
- OTPs support persistent storage in Supabase (`otp_codes`) with expiry and in-memory fallback

## Repository Structure

```text
.
├─ backend/
│  ├─ main.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/...
│  └─ package.json
├─ database.sql
├─ render.yaml
└─ README.md
```

## Environment Variables

### Backend (`backend/.env` or Render env vars)

```env
GEMINI_API_KEY=
HUGGINGFACE_API_KEY=
HUGGINGFACE_API_URL=https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
JWT_SECRET=
CORS_ORIGINS=https://latexify-mu.vercel.app
FRONTEND_URL=https://latexify-mu.vercel.app
```

### Frontend (`frontend/.env.local` or Vercel env vars)

```env
NEXT_PUBLIC_API_URL=https://latexify-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## Database Setup

Run [database.sql](d:/CODES/Latexify/database.sql) in Supabase SQL Editor to create/update:

- `public."Documents"` (+ `user_email`)
- optional lowercase `public.documents` compatibility path
- `public.otp_codes`
- RLS/security policies and grants

## Local Development

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:3000`

## Deployment Notes

- Backend is deployed from [render.yaml](d:/CODES/Latexify/render.yaml) using [backend/Dockerfile](d:/CODES/Latexify/backend/Dockerfile)
- Ensure Render env vars include `CORS_ORIGINS` and `JWT_SECRET`
- Ensure Vercel frontend points to the Render backend URL

## Current Product Strengths (Buyer Summary)

- Full-stack deployed SaaS with working auth, generation, compilation, and history
- Handles real LaTeX workflows: templates, citations, and PDF rendering
- Robust fallback strategy across multiple LLM providers
- Security posture improved with RLS and scoped backend access
- Extensible architecture for teams, premium templates, and enterprise controls

## Author

Anustup Maity  
GitHub: `https://github.com/AnustupMaity`
