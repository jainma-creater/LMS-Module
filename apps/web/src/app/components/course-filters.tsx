import Link from "next/link";

import { Field, inputClass } from "./fields";

export interface CatalogQuery {
  search?: string;
  category?: string;
  difficulty_level?: string;
  tag?: string;
}

const DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;

// Plain GET form: works without client JavaScript and keeps filters in the URL.
export function CourseFilters({
  query,
  categories,
}: {
  query: CatalogQuery;
  categories: string[];
}) {
  return (
    <form
      method="get"
      action="/courses"
      role="search"
      className="grid gap-3 rounded-xl border border-[var(--border)] bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5"
    >
      <div className="sm:col-span-2 lg:col-span-2">
        <Field label="Search">
          <input
            type="search"
            name="search"
            defaultValue={query.search ?? ""}
            placeholder="Title or summary"
            maxLength={200}
            className={inputClass}
          />
        </Field>
      </div>
      <Field label="Category">
        <select name="category" defaultValue={query.category ?? ""} className={inputClass}>
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Difficulty">
        <select
          name="difficulty_level"
          defaultValue={query.difficulty_level ?? ""}
          className={inputClass}
        >
          <option value="">Any level</option>
          {DIFFICULTIES.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Tag">
        <input
          type="text"
          name="tag"
          defaultValue={query.tag ?? ""}
          placeholder="e.g. security"
          maxLength={50}
          className={inputClass}
        />
      </Field>
      <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-5">
        <button type="submit" className="brand-button">
          Apply filters
        </button>
        <Link href="/courses" className="text-sm text-zinc-600 hover:text-[var(--brand)]">
          Clear
        </Link>
      </div>
    </form>
  );
}
