"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils/cn";

const TABS = [
  { href: "/market-data", label: "Market Data" },
  { href: "/log-analyzer", label: "Log Analyzer" },
];

export function TopNav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/95 backdrop-blur">
      <div className="flex items-center gap-6 px-4 h-12">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          IMC<span className="text-accent">·</span>Prosperity
        </Link>
        <nav className="flex items-center gap-1">
          {TABS.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm transition-colors",
                pathname?.startsWith(t.href)
                  ? "bg-panel text-text"
                  : "text-muted hover:text-text"
              )}
            >
              {t.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
