"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/manage", label: "Overview", exact: true },
  { href: "/manage/studio", label: "AI Studio" },
  { href: "/manage/learners", label: "Learners" },
  { href: "/manage/groups", label: "Groups" },
  { href: "/manage/assignments", label: "Assignments" },
  { href: "/manage/group-assignments", label: "Group Assignments" },
];

export default function AdminNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Admin sections" className="flex flex-col gap-1">
      {LINKS.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              active
                ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                : "text-zinc-600 hover:bg-[var(--surface-muted)]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
