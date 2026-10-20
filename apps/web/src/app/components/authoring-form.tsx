"use client";

import { createContext, startTransition, useActionState, useContext, useEffect, useRef } from "react";
import type { FormEvent, ReactNode } from "react";

import { initialFormState, type FormAction } from "@/lib/form";

import { inputClass } from "./fields";

interface FieldContextValue {
  idPrefix: string;
  errors: Record<string, string>;
}

const FieldContext = createContext<FieldContextValue>({ idPrefix: "f", errors: {} });

/**
 * Wraps an authoring form.
 *
 * The form is NOT a native `<form action>`: React resets native form-action forms
 * after every submission, which would discard the user's edits when the save
 * fails. Here the submit handler dispatches the action manually, so the inputs
 * keep what the user typed. Field errors come back in `state.fieldErrors`.
 */
export function AuthoringForm({
  action,
  idPrefix,
  submitLabel,
  pendingLabel = "Saving…",
  resetOnSuccess = false,
  className,
  children,
}: {
  action: FormAction;
  idPrefix: string;
  submitLabel: string;
  pendingLabel?: string;
  resetOnSuccess?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const [state, dispatch, pending] = useActionState(action, initialFormState);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (resetOnSuccess && state.status === "success") {
      formRef.current?.reset();
    }
  }, [state, resetOnSuccess]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    startTransition(() => {
      dispatch(formData);
    });
  }

  const errors = state.fieldErrors ?? {};

  return (
    <FieldContext.Provider value={{ idPrefix, errors }}>
      <form
        ref={formRef}
        noValidate
        onSubmit={onSubmit}
        aria-busy={pending}
        className={className ?? "flex flex-col gap-3"}
      >
        {state.status === "error" ? (
          <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            {state.message}
          </p>
        ) : null}
        {state.status === "success" ? (
          <p role="status" className="text-sm text-green-700 dark:text-green-400">
            {state.message}
          </p>
        ) : null}
        {children}
        <div>
          <button
            type="submit"
            disabled={pending}
            className="inline-flex items-center rounded-md bg-black px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
          >
            {pending ? pendingLabel : submitLabel}
          </button>
        </div>
      </form>
    </FieldContext.Provider>
  );
}

function useFieldState(name: string) {
  const { idPrefix, errors } = useContext(FieldContext);
  const id = `${idPrefix}-${name}`;
  const error = errors[name];
  return {
    id,
    error,
    describedBy: error ? `${id}-error` : undefined,
    invalid: error ? true : undefined,
  };
}

interface CommonProps {
  name: string;
  label: string;
  hint?: string;
  required?: boolean;
  defaultValue?: string;
}

function FieldFrame({
  id,
  label,
  hint,
  error,
  required,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label htmlFor={id} className="font-medium text-zinc-700 dark:text-zinc-300">
        {label}
        {required ? <span className="text-red-600 dark:text-red-400"> *</span> : null}
      </label>
      {children}
      {hint ? <span className="text-xs text-zinc-500 dark:text-zinc-400">{hint}</span> : null}
      {error ? (
        <span id={`${id}-error`} className="text-xs font-medium text-red-600 dark:text-red-400">
          {error}
        </span>
      ) : null}
    </div>
  );
}

export function TextField({
  name,
  label,
  hint,
  required,
  defaultValue,
  type = "text",
  maxLength,
  placeholder,
  min,
  max,
}: CommonProps & {
  type?: "text" | "number" | "search" | "url";
  maxLength?: number;
  placeholder?: string;
  min?: number;
  max?: number;
}) {
  const field = useFieldState(name);
  return (
    <FieldFrame id={field.id} label={label} hint={hint} error={field.error} required={required}>
      <input
        id={field.id}
        name={name}
        type={type}
        defaultValue={defaultValue}
        maxLength={maxLength}
        placeholder={placeholder}
        min={min}
        max={max}
        required={required}
        aria-required={required || undefined}
        aria-invalid={field.invalid}
        aria-describedby={field.describedBy}
        className={inputClass}
      />
    </FieldFrame>
  );
}

export function TextAreaField({
  name,
  label,
  hint,
  required,
  defaultValue,
  rows = 3,
  maxLength,
}: CommonProps & { rows?: number; maxLength?: number }) {
  const field = useFieldState(name);
  return (
    <FieldFrame id={field.id} label={label} hint={hint} error={field.error} required={required}>
      <textarea
        id={field.id}
        name={name}
        rows={rows}
        defaultValue={defaultValue}
        maxLength={maxLength}
        required={required}
        aria-required={required || undefined}
        aria-invalid={field.invalid}
        aria-describedby={field.describedBy}
        className={inputClass}
      />
    </FieldFrame>
  );
}

export function SelectField({
  name,
  label,
  hint,
  defaultValue,
  options,
  onChange,
}: CommonProps & {
  options: { value: string; label: string }[];
  onChange?: (value: string) => void;
}) {
  const field = useFieldState(name);
  return (
    <FieldFrame id={field.id} label={label} hint={hint} error={field.error}>
      <select
        id={field.id}
        name={name}
        defaultValue={defaultValue}
        onChange={onChange ? (event) => onChange(event.currentTarget.value) : undefined}
        aria-invalid={field.invalid}
        aria-describedby={field.describedBy}
        className={inputClass}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldFrame>
  );
}

export function CheckboxField({
  name,
  label,
  defaultChecked,
}: {
  name: string;
  label: string;
  defaultChecked?: boolean;
}) {
  const field = useFieldState(name);
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label className="flex items-center gap-2">
        <input
          id={field.id}
          type="checkbox"
          name={name}
          defaultChecked={defaultChecked}
          aria-invalid={field.invalid}
        />
        {label}
      </label>
      {field.error ? (
        <span id={`${field.id}-error`} className="text-xs font-medium text-red-600 dark:text-red-400">
          {field.error}
        </span>
      ) : null}
    </div>
  );
}
