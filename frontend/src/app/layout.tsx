import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { QueryProvider } from "@/components/providers/query-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import { ThemeProvider, themeInitScript } from "@/components/providers/theme-provider";
import { ToastProvider } from "@/components/ui/toast";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "FlowForge", template: "%s · FlowForge" },
  description: "Open-source visual workflow automation platform for developers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <a
          href="#main"
          className="focus:bg-accent focus:text-accent-fg sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded focus:px-3 focus:py-2 focus:text-sm"
        >
          Skip to content
        </a>
        <ThemeProvider>
          <QueryProvider>
            <SessionProvider>
              <ToastProvider>{children}</ToastProvider>
            </SessionProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
