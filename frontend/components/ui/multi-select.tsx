"use client";
import { cn } from "@/lib/utils/cn";

interface Props<T extends string | number> {
  options: T[];
  value: T[];
  onChange: (next: T[]) => void;
  className?: string;
}

export function MultiSelect<T extends string | number>({ options, value, onChange, className }: Props<T>) {
  const toggle = (v: T) =>
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {options.map((opt) => {
        const active = value.includes(opt);
        return (
          <button
            key={String(opt)}
            type="button"
            onClick={() => toggle(opt)}
            className={cn(
              "rounded-md px-2 h-7 text-xs border transition-colors",
              active
                ? "border-accent bg-accent/15 text-accent"
                : "border-border bg-bg text-muted hover:text-text",
            )}
          >
            {String(opt)}
          </button>
        );
      })}
    </div>
  );
}
