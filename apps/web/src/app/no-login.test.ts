// Static guard: the development build has no sign-in page, login route, or
// login redirect. Run with: npm test (from apps/web).
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, it } from "node:test";

const WEB_ROOT = process.cwd();
const SRC = join(WEB_ROOT, "src");
const SELF_NAME = "no-login.test.ts";

const LOGIN_ROUTE_NAMES = ["login", "signin", "sign-in", "sign_in", "auth", "logout", "register"];
const LOGIN_REFERENCE = /(["'`])\/(login|signin|sign-in|auth|logout)(["'/`?#])/i;

function listFiles(dir: string): string[] {
  return readdirSync(dir, { recursive: true })
    .map((entry) => join(dir, String(entry)))
    .filter((path) => statSync(path).isFile());
}

describe("development build has no login surface", () => {
  it("has no login, sign-in, or auth route directories under src/app", () => {
    const dirs = readdirSync(join(SRC, "app"), { recursive: true })
      .map((entry) => String(entry))
      .filter((entry) => statSync(join(SRC, "app", entry)).isDirectory())
      .map((entry) => entry.split(/[\\/]/).pop() ?? "");
    for (const name of LOGIN_ROUTE_NAMES) {
      assert.ok(!dirs.includes(name), `unexpected login-like route directory: ${name}`);
    }
  });

  it("has no request middleware or proxy that could redirect to a login page", () => {
    for (const file of ["middleware.ts", "middleware.js", "proxy.ts", "proxy.js"]) {
      assert.equal(existsSync(join(SRC, file)), false, `${file} must not exist in src`);
      assert.equal(existsSync(join(WEB_ROOT, file)), false, `${file} must not exist at root`);
    }
  });

  it("contains no references to login or sign-in URLs in application source", () => {
    const offenders: string[] = [];
    for (const file of listFiles(SRC)) {
      if (file.endsWith(SELF_NAME)) continue;
      if (!/\.(tsx?|jsx?|css|md)$/.test(file)) continue;
      const text = readFileSync(file, "utf8");
      if (LOGIN_REFERENCE.test(text)) offenders.push(relative(WEB_ROOT, file));
    }
    assert.deepEqual(offenders, []);
  });
});
