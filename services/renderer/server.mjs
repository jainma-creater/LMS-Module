// HTTP wrapper around Remotion for AI Training Studio course videos.
//
//   POST /render   JSON {job_id, course_title, accent_color, scenes[], narration_wav_base64?}
//                  -> {ok, output_file, duration_frames}
//   GET  /health   -> {ok, bundled}
//
// Renders are serialized (one at a time). Narration audio is written to a
// local directory and served on localhost so headless Chromium can load it.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const here = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8080);
const OUTPUT_DIR = process.env.OUTPUT_DIR || path.join(here, "out");
const NARRATION_DIR = process.env.NARRATION_DIR || path.join(here, "narration");
const MAX_BODY_BYTES = 80 * 1024 * 1024;
const JOB_ID_RE = /^[A-Za-z0-9_-]{1,64}$/;
const COMPOSITION_ID = "CourseVideo";

fs.mkdirSync(OUTPUT_DIR, { recursive: true });
fs.mkdirSync(NARRATION_DIR, { recursive: true });

let serveUrl = null;
let queue = Promise.resolve();

async function ensureBundle() {
  if (!serveUrl) {
    serveUrl = await bundle({ entryPoint: path.join(here, "src", "index.ts") });
  }
  return serveUrl;
}

function sendJson(res, status, body) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(Object.assign(new Error("Request body too large"), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function validatePayload(payload) {
  if (!payload || typeof payload !== "object") throw new Error("payload must be an object");
  if (!JOB_ID_RE.test(String(payload.job_id || ""))) throw new Error("invalid job_id");
  if (!Array.isArray(payload.scenes) || payload.scenes.length === 0) {
    throw new Error("scenes must be a non-empty array");
  }
  if (payload.scenes.length > 40) throw new Error("too many scenes (max 40)");
  for (const s of payload.scenes) {
    if (typeof s.title !== "string" || !s.title.trim()) throw new Error("scene title required");
    if (!Array.isArray(s.bullets)) throw new Error("scene bullets must be an array");
    const d = Number(s.duration_sec);
    if (!Number.isFinite(d) || d <= 0 || d > 600) throw new Error("scene duration_sec out of range");
  }
}

async function renderJob(payload) {
  validatePayload(payload);
  const jobId = payload.job_id;

  let narrationSrc = null;
  if (payload.narration_wav_base64) {
    const wav = Buffer.from(payload.narration_wav_base64, "base64");
    if (wav.length < 44 || wav.toString("ascii", 0, 4) !== "RIFF") {
      throw new Error("narration must be a WAV file");
    }
    fs.writeFileSync(path.join(NARRATION_DIR, `${jobId}.wav`), wav);
    narrationSrc = `http://127.0.0.1:${PORT}/narration/${jobId}.wav`;
  }

  const inputProps = {
    courseTitle: String(payload.course_title || "").slice(0, 200),
    accentColor: /^#[0-9A-Fa-f]{6}$/.test(payload.accent_color || "") ? payload.accent_color : "#38BDF8",
    narrationSrc,
    scenes: payload.scenes.map((s) => ({
      title: String(s.title).slice(0, 200),
      kicker: String(s.kicker || "").slice(0, 60),
      bullets: s.bullets.slice(0, 8).map((b) => String(b).slice(0, 240)),
      narration: String(s.narration || "").slice(0, 1200),
      durationSec: Number(s.duration_sec),
    })),
  };

  const url = await ensureBundle();
  const composition = await selectComposition({ serveUrl: url, id: COMPOSITION_ID, inputProps });
  const outputFile = path.join(OUTPUT_DIR, `video_${jobId}.mp4`);
  await renderMedia({
    composition,
    serveUrl: url,
    codec: "h264",
    outputLocation: outputFile,
    inputProps,
    timeoutInMilliseconds: 600_000,
  });
  const stat = fs.statSync(outputFile);
  if (stat.size < 1024) throw new Error("render produced an empty file");
  return { ok: true, output_file: outputFile, duration_frames: composition.durationInFrames };
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") {
      return sendJson(res, 200, { ok: true, bundled: serveUrl !== null });
    }
    if (req.method === "GET" && req.url?.startsWith("/narration/")) {
      const name = path.basename(req.url);
      if (!/^[A-Za-z0-9_-]+\.wav$/.test(name)) return sendJson(res, 404, { error: "not found" });
      const file = path.join(NARRATION_DIR, name);
      if (!fs.existsSync(file)) return sendJson(res, 404, { error: "not found" });
      res.writeHead(200, { "content-type": "audio/wav", "access-control-allow-origin": "*" });
      return fs.createReadStream(file).pipe(res);
    }
    if (req.method === "POST" && req.url === "/render") {
      const raw = await readBody(req);
      const payload = JSON.parse(raw);
      const job = queue.then(() => renderJob(payload));
      queue = job.catch(() => {});
      const result = await job;
      return sendJson(res, 200, result);
    }
    return sendJson(res, 404, { error: "not found" });
  } catch (err) {
    const status = err.status || (err instanceof SyntaxError ? 400 : err.message?.startsWith("invalid") || err.message?.includes("must") || err.message?.includes("required") || err.message?.includes("out of range") || err.message?.includes("too many") || err.message?.includes("WAV") ? 422 : 500);
    console.error("render error:", err);
    return sendJson(res, status, { ok: false, error: String(err.message || err) });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`course renderer listening on ${PORT}`);
  ensureBundle()
    .then(() => console.log("composition bundled"))
    .catch((err) => console.error("bundle failed:", err));
});
