import type { ReactNode } from "react";

import type { ApiErrorKind } from "@/lib/api";

function toneClasses(tone: "info" | "success" | "warning" | "error"): string {
  switch (tone) {
    case "success":
      return "border-[#bfe3cd] bg-[var(--accent-success-soft)] text-[var(--accent-success)]";
    case "warning":
      return "border-amber-300 bg-[var(--accent-warning-soft)] text-[var(--accent-warning)]";
    case "error":
      return "border-red-300 bg-[var(--accent-danger-soft)] text-[var(--accent-danger)]";
    default:
      return "border-[var(--border)] bg-[var(--surface-muted)] text-zinc-700";
  }
}

export function Notice({
  tone = "info",
  children,
}: {
  tone?: "info" | "success" | "warning" | "error";
  children: ReactNode;
}) {
  return (
    <p role="status" className={`rounded-lg border px-4 py-3 text-sm ${toneClasses(tone)}`}>
      {children}
    </p>
  );
}

export function AccessNotice({ kind, message }: { kind: ApiErrorKind; message: string }) {
  if (kind === "unauthorized" || kind === "forbidden") {
    return (
      <Notice tone="warning">
        <strong className="font-medium">Access unavailable.</strong> {message}
      </Notice>
    );
  }
  if (kind === "not_found") {
    return <Notice tone="info">Not found. {message}</Notice>;
  }
  return (
    <Notice tone={kind === "network" || kind === "server" ? "error" : "warning"}>{message}</Notice>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-muted)] px-6 py-12 text-center">
      <p className="font-medium text-zinc-800">{title}</p>
      <p className="max-w-md text-sm text-zinc-500">{description}</p>
      {action}
    </div>
  );
}

const STATUS_TONES: Record<string, string> = {
  published: "bg-[var(--accent-success-soft)] text-[var(--accent-success)]",
  draft: "bg-[var(--accent-warning-soft)] text-[var(--accent-warning)]",
  archived: "bg-[var(--surface-sunken)] text-zinc-600",
  completed: "bg-[var(--accent-success-soft)] text-[var(--accent-success)]",
  in_progress: "bg-[var(--brand-soft)] text-[var(--brand-strong)]",
  assigned: "bg-[var(--surface-sunken)] text-zinc-600",
  active: "bg-[var(--accent-success-soft)] text-[var(--accent-success)]",
  cancelled: "bg-[var(--accent-danger-soft)] text-[var(--accent-danger)]",
  withdrawn: "bg-[var(--surface-sunken)] text-zinc-600",
  overdue: "bg-[var(--accent-danger-soft)] text-[var(--accent-danger)]",
  generated: "bg-[var(--brand-soft)] text-[var(--brand-strong)]",
  processing: "bg-[var(--accent-warning-soft)] text-[var(--accent-warning)]",
  pending: "bg-[var(--surface-sunken)] text-zinc-600",
  failed: "bg-[var(--accent-danger-soft)] text-[var(--accent-danger)]",
};

export function StatusBadge({ value }: { value: string }) {
  const tone = STATUS_TONES[value] ?? "bg-[var(--surface-sunken)] text-zinc-600";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${tone}`}>
      {value.replace(/_/g, " ")}
    </span>
  );
}

export function ProgressMeter({
  value,
  label,
  tone = "brand",
}: {
  value: number;
  label?: string;
  tone?: "brand" | "success";
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  const bar = tone === "success" ? "var(--accent-success)" : "var(--brand)";
  return (
    <div className="w-full">
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--surface-sunken)]">
        <div className="h-full rounded-full transition-[width]" style={{ width: `${clamped}%`, backgroundColor: bar }} />
      </div>
      <p className="mt-1 text-xs text-zinc-500">{label ?? `${clamped}% complete`}</p>
    </div>
  );
}

export function ProgressRing({ value, size = 56 }: { value: number; size?: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const stroke = 5;
  const radius = (48 - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = (clamped / 100) * circumference;
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      role="img"
      aria-label={`${clamped}% complete`}
      className="shrink-0"
    >
      <circle cx="24" cy="24" r={radius} fill="none" stroke="var(--surface-sunken)" strokeWidth={stroke} />
      <circle
        cx="24"
        cy="24"
        r={radius}
        fill="none"
        stroke="var(--brand)"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circumference - dash}`}
        transform="rotate(-90 24 24)"
      />
      <text x="24" y="26" textAnchor="middle" className="fill-zinc-700 text-[11px] font-semibold">
        {clamped}%
      </text>
    </svg>
  );
}

export function PageHeader({
  title,
  description,
  action,
  eyebrow,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow ? (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--brand)]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 sm:text-3xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 text-sm text-[var(--muted-foreground)]">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function Card({
  title,
  meta,
  children,
  footer,
  className = "",
}: {
  title?: ReactNode;
  meta?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <article
      className={`flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm ${className}`}
    >
      {title ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-medium text-zinc-900">{title}</h2>
          {meta}
        </div>
      ) : null}
      <div className="text-sm text-[var(--muted-foreground)]">{children}</div>
      {footer ? <div className="mt-1">{footer}</div> : null}
    </article>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-zinc-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-zinc-500">{hint}</p> : null}
    </div>
  );
}
