"use client";

import Link from "next/link";

import type { LearningGroup } from "@/lib/types";

import { StatusBadge } from "./ui";

interface GroupTableProps {
  groups: LearningGroup[];
}

export function GroupTable({ groups }: GroupTableProps) {
  if (groups.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
        <p className="font-medium text-zinc-800 dark:text-zinc-200">No groups found</p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Create your first group to begin organizing learners.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800" role="table">
        <thead className="bg-zinc-50 dark:bg-zinc-900">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Name
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Kind
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Members
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-zinc-950 divide-y divide-zinc-200 dark:divide-zinc-800">
          {groups.map((group) => (
            <tr key={group.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-zinc-900 dark:text-zinc-100">
                <Link href={`/manage/groups/${group.id}`} className="hover:underline">
                  {group.name}
                </Link>
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-600 dark:text-zinc-400 capitalize">
                {group.kind}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-600 dark:text-zinc-400">
                {group.member_count}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <StatusBadge value={group.status} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <Link
                  href={`/manage/groups/${group.id}`}
                  className="text-blue-700 hover:underline dark:text-blue-400"
                >
                  Manage
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}