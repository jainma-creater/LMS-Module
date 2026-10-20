"use client";

import { useActionState } from "react";
import type { ReactNode } from "react";

import { initialFormState, type FormAction } from "@/lib/form";

export default function ActionForm({
  action,
  submitLabel,
  children,
  className,
}: {
  action: FormAction;
  submitLabel: string;
  children?: ReactNode;
  className?: string;
}) {
  const [state, formAction, pending] = useActionState(action, initialFormState);

  return (
    <form action={formAction} className={className ?? "flex flex-col gap-3"}>
      {children}
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={pending} className="brand-button disabled:opacity-60">
          {pending ? "Working…" : submitLabel}
        </button>
        {state.status === "error" ? (
          <p role="alert" className="text-sm text-[var(--accent-danger)]">
            {state.message}
          </p>
        ) : null}
        {state.status === "success" ? (
          <p role="status" className="text-sm text-[var(--accent-success)]">
            {state.message}
          </p>
        ) : null}
      </div>
    </form>
  );
}
