# LaTeXify AI 🤖📝

[![Live App](https://img.shields.io/badge/Live_App-latexify--mu.vercel.app-green?style=for-the-badge&logo=vercel)](https://latexify-mu.vercel.app/)

**LaTeXify AI** is a self-healing, agentic AI platform that instantly converts user text, notes, and instructions into high-quality, natively compiled LaTeX code and PDFs. 

It doesn't just generate code — if the LaTeX TeX Live compiler throws an error, the backend automatically captures the log, feeds it back to the AI, and patches the code until it compiles perfectly.

---

## 🏗️ Architecture & Deployment

LaTeXify AI is built as a complete Monorepo encompassing both the frontend application and the self-healing compilation engine.

- **[🖥️ Frontend](https://latexify-mu.vercel.app/):** Built using **Next.js 15 (App Router)** and **Tailwind CSS v4**. It utilizes an aesthetic glassmorphism UI and dynamically fetches history and compilation states.
  - **Deployed on:** [Vercel](https://vercel.com) (Serverless Edge)
  
- **[⚙️ Backend](https://latexify-backend.onrender.com):** A **FastAPI Python** engine containing the AI fallback chain model (Gemini Pro → HuggingFace) and a native TeX Live environment via `pdflatex` to process document builds securely and quickly using `subprocess`.
  - **Deployed on:** [Render.com](https://render.com) (Docker Runtime Environment)
  
- **[🗄️ Database]:** **Supabase (PostgreSQL)** is utilized to store generation histories, documents, and compile statuses.
  
- **[📧 Authentication]:** A custom-built secure Email OTP flow powered natively by the **Brevo REST API**, bypassing standard third-party magic links.

---

## ✨ Key Features

1. **AI-Powered Code Generation:** Pass abstract notes or assignment requirements, and get precise LaTeX structures tailored to parameters (e.g., IEEE format, standard format).
2. **Self-Healing Loop Engine:** LaTeX is notoriously difficult to compile manually. If the backend `pdflatex` engine encounters an error, the log is piped directly back to the AI to auto-fix and retry (up to 3 iterations).
3. **Live PDF Preview:** Integrated embedded PDF `<Iframe>` viewers straight in the browser.
4. **Secure OTP Handlers:** Passwordless 6-digit PIN login managed directly between Python and Brevo.
5. **No Docker-in-Docker required:** Fully containerized backend image utilizing a base Ubuntu image bundled with both Python & native TeX Live distribution.

---

## 🚀 Running Locally

### 1. Requirements
Ensure you have the following installed on your machine:
- Node.js (v18+)
- Python (3.10+)
- Postgres/Supabase instance
- TeX Live (if running the Python engine locally natively without Docker)

### 2. Environment Variables

You will need to set up the following keys across your environments.

**`frontend/.env.local`**
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**`backend/.env`**
```env
GEMINI_API_KEY=your_gemini_key
HUGGINGFACE_API_KEY=your_hf_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role
SUPABASE_DB_URL=your_postgres_connection_string
BREVO_API_KEY=your_brevo_api
BREVO_SENDER_EMAIL=your_verified_brevo_sender_email
```

### 3. Start the Application

**Start the Backend (FastAPI)**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Start the Frontend (Next.js)**
```bash
cd frontend
npm install
npm run dev
```

Visit [`http://localhost:3000`](http://localhost:3000)

---
*Created by [Anustup Maity](https://github.com/AnustupMaity)*
