"use client";

import Link from "next/link";

import type { GroupAssignmentView } from "@/lib/types";

import { StatusBadge } from "./ui";

interface GroupAssignmentTableProps {
  groupAssignments: GroupAssignmentView[];
}

export function GroupAssignmentTable({ groupAssignments }: GroupAssignmentTableProps) {
  if (groupAssignments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
        <p className="font-medium text-zinc-800 dark:text-zinc-200">No group assignments found</p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Assign courses to groups to get started.
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
              Course
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Group
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Due Date
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-zinc-950 divide-y divide-zinc-200 dark:divide-zinc-800">
          {groupAssignments.map((ga) => (
            <tr key={ga.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-zinc-900 dark:text-zinc-100">
                <Link href={`/courses/${ga.course_id}`} className="hover:underline">
                  {ga.course_title}
                </Link>
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-zinc-900 dark:text-zinc-100">
                <Link href={`/manage/groups/${ga.group_id}`} className="hover:underline">
                  {ga.group_name}
                </Link>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <StatusBadge value={ga.status} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-600 dark:text-zinc-400">
                {ga.due_at ? new Date(ga.due_at).toLocaleDateString() : "—"}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <Link href={`/manage/group-assignments/${ga.id}`} className="text-blue-700 hover:underline dark:text-blue-400">
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