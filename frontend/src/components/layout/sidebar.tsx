"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GitBranch, LayoutDashboard, ListChecks, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { cn } from "@/lib/cn";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
  { href: "/executions", label: "Executions", icon: ListChecks },
  { href: "/templates", label: "Templates", icon: Sparkles },
];

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5 p-2">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
              active
                ? "bg-accent-soft text-accent font-medium"
                : "text-text-muted hover:bg-surface hover:text-text",
            )}
          >
            <Icon aria-hidden className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  return (
    <aside className="border-border-base bg-surface hidden w-56 shrink-0 flex-col border-r md:flex">
      <Link
        href="/dashboard"
        className="border-border-base text-text flex h-14 items-center gap-2 border-b px-4"
      >
        <Logo className="text-accent" />
        <span className="text-sm font-semibold tracking-tight">FlowForge</span>
      </Link>
      <SidebarNav />
    </aside>
  );
}
