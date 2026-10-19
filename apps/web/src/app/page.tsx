import { Suspense } from "react";

import BackendStatus from "./backend-status";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-2xl flex-col gap-6 px-8 py-24">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            AI LMS
          </h1>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Platform foundation. Authentication, courses, and AI features arrive
            in later milestones.
          </p>
        </div>
        <Suspense
          fallback={
            <p className="text-sm text-zinc-500" role="status">
              Checking API status…
            </p>
          }
        >
          <BackendStatus />
        </Suspense>
      </main>
    </div>
  );
}
