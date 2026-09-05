"use client";

import { useState } from "react";
import Link from "next/link";
import { LogOut, Menu, Moon, Sun, X } from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { SidebarNav } from "@/components/layout/sidebar";
import { useSession } from "@/components/providers/session-provider";
import { useTheme } from "@/components/providers/theme-provider";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { user, signOut } = useSession();
  const { theme, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <header className="border-border-base bg-bg flex h-14 shrink-0 items-center justify-between gap-3 border-b px-4">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          >
            {menuOpen ? (
              <X aria-hidden className="h-4 w-4" />
            ) : (
              <Menu aria-hidden className="h-4 w-4" />
            )}
          </Button>
          <Link href="/dashboard" className="flex items-center gap-2 md:hidden">
            <Logo className="text-accent" />
            <span className="text-sm font-semibold">FlowForge</span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? (
              <Sun aria-hidden className="h-4 w-4" />
            ) : (
              <Moon aria-hidden className="h-4 w-4" />
            )}
          </Button>
          {user && (
            <>
              <span className="text-text-muted hidden text-sm sm:inline" title={user.email}>
                {user.name}
              </span>
              <Button variant="ghost" size="sm" onClick={() => void signOut()}>
                <LogOut aria-hidden className="h-3.5 w-3.5" />
                Sign out
              </Button>
            </>
          )}
        </div>
      </header>

      {menuOpen && (
        <div id="mobile-navigation" className="border-border-base bg-surface border-b md:hidden">
          <SidebarNav onNavigate={() => setMenuOpen(false)} />
        </div>
      )}
    </>
  );
}
