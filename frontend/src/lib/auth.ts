export function isTokenExpired(token: string): boolean {
  try {
    const payloadPart = token.split(".")[1];
    if (!payloadPart) return true;
    const payload = JSON.parse(atob(payloadPart));
    const exp = payload?.exp;
    if (typeof exp !== "number") return true;
    return Date.now() >= exp * 1000;
  } catch {
    return true;
  }
}

export function clearSessionAndRedirect() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("email");
  window.location.href = "/login";
}
