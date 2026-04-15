// Central API base URL — reads from env var so it works locally and on Vercel/prod
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default API_BASE;
