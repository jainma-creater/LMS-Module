"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SearchBox({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    router.push(trimmed ? `/courses?search=${encodeURIComponent(trimmed)}` : "/courses");
  }

  return (
    <form
      role="search"
      onSubmit={submit}
      className="flex h-10 w-full items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-4 focus-within:border-[var(--brand)] focus-within:bg-white"
    >
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-4 w-4 shrink-0 text-zinc-500"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="7" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <label htmlFor="site-search" className="sr-only">
        Search courses
      </label>
      <input
        id="site-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="What do you want to learn?"
        className="h-full w-full bg-transparent text-sm outline-none placeholder:text-zinc-500"
      />
    </form>
  );
}
