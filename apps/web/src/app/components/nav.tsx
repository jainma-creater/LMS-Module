import Link from "next/link";

import SearchBox from "./search-box";

const LEARNER_LINKS = [
  { href: "/courses", label: "Catalog" },
  { href: "/learning", label: "My Learning" },
  { href: "/progress", label: "Progress" },
];

const ADMIN_LINKS = [
  { href: "/manage", label: "Manage" },
  { href: "/manage/studio", label: "AI Studio" },
  { href: "/manage/learners", label: "Learners" },
  { href: "/manage/assignments", label: "Assignments" },
];

function BrandMark() {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className="grid h-7 w-7 place-items-center rounded-md text-sm font-bold text-white"
        style={{ backgroundColor: "var(--brand)" }}
      >
        AI
      </span>
      <span className="text-base font-semibold tracking-tight text-zinc-900">
        LMS
      </span>
    </span>
  );
}

export default function SiteNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" aria-label="AI LMS home" className="shrink-0">
          <BrandMark />
        </Link>

        <div className="hidden min-w-0 flex-1 sm:block">
          <SearchBox />
        </div>

        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {LEARNER_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-600 transition-colors hover:bg-[var(--surface-muted)] hover:text-[var(--brand)]"
            >
              {link.label}
            </Link>
          ))}
          <span aria-hidden="true" className="mx-1 h-5 w-px bg-[var(--border)]" />
          {ADMIN_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-600 transition-colors hover:bg-[var(--surface-muted)] hover:text-[var(--brand)]"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="border-t border-[var(--border)] px-4 py-2 sm:hidden">
        <SearchBox />
      </div>
    </header>
  );
}
