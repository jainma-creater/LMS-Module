import { getBackendHealth } from "@/lib/health";

export default async function BackendStatus() {
  const health = await getBackendHealth();

  if (health.state === "up") {
    return (
      <p
        className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200"
        role="status"
      >
        API connected ({health.appName}).
      </p>
    );
  }

  return (
    <p
      className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
      role="status"
    >
      API not reachable. Start the backend with{" "}
      <code className="font-mono">docker compose up</code> or run it locally.
    </p>
  );
}
