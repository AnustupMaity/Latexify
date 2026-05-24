"use client";

import { LogOut } from "lucide-react";
import { clearSessionAndRedirect } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LogoutButton() {
  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, { method: "POST" });
    } catch (e) {
      console.error("Logout failed", e);
    }
    clearSessionAndRedirect();
  };

  return (
    <button
      onClick={handleLogout}
      className="flex w-full items-center gap-3 px-3 py-2 text-muted-foreground hover:text-foreground transition-colors text-sm font-medium rounded-lg hover:bg-secondary/50"
    >
      <LogOut className="w-4 h-4" />
      Logout
    </button>
  );
}
