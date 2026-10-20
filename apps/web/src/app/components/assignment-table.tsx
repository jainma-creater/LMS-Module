"use client";

import Link from "next/link";

import type { AssignmentView } from "@/lib/types";

import { StatusBadge } from "./ui";

interface AssignmentTableProps {
  assignments: AssignmentView[];
}

export function AssignmentTable({ assignments }: AssignmentTableProps) {
  if (assignments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
        <p className="font-medium text-zinc-800 dark:text-zinc-200">No assignments found</p>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Assign courses to learners or groups to get started.
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
              Learner
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Source
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Due Date
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Overdue
            </th>
            <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider dark:text-zinc-400">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-zinc-950 divide-y divide-zinc-200 dark:divide-zinc-800">
          {assignments.map((assignment) => (
            <tr key={assignment.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-zinc-900 dark:text-zinc-100">
                <Link href={`/courses/${assignment.course_id}`} className="hover:underline">
                  {assignment.course_title}
                </Link>
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-900 dark:text-zinc-100">
                {assignment.learner_name}
                <span className="ml-2 text-xs text-zinc-500 font-mono">({assignment.learner_employee_id})</span>
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-600 dark:text-zinc-400 capitalize">
                {assignment.source}
                {assignment.group_name && (
                  <span className="ml-1 text-xs text-zinc-500">
                    ({assignment.group_name})
                  </span>
                )}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                <StatusBadge value={assignment.derived_status} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-zinc-600 dark:text-zinc-400">
                {assignment.due_at ? new Date(assignment.due_at).toLocaleDateString() : "—"}
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                {assignment.overdue ? (
                  <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900 dark:text-red-200">
                    Yes
                  </span>
                ) : (
                  <span className="text-zinc-500">No</span>
                )}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <Link
                  href={`/manage/assignments/${assignment.id}`}
                  className="text-blue-700 hover:underline dark:text-blue-400"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}