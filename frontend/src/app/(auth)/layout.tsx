import { Logo } from "@/components/layout/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-surface flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="text-text mb-6 flex items-center gap-2">
        <Logo className="text-accent h-6 w-6" />
        <span className="text-base font-semibold tracking-tight">FlowForge</span>
      </div>
      <main className="border-border-base bg-bg w-full max-w-sm rounded-lg border p-6">
        {children}
      </main>
      <p className="text-text-subtle mt-6 max-w-sm text-center text-xs">
        Open-source visual workflow automation platform for developers.
      </p>
    </div>
  );
}
