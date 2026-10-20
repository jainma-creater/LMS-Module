// Run with: npm test  (Node built-in test runner; no extra dependencies)
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  isHttpUrl,
  LIMITS,
  parseMinutes,
  parseTags,
  validateCourseInput,
  validateLessonInput,
} from "./authoring.ts";

const validCourse = { title: "Fire Safety", difficulty_level: "beginner" };

describe("isHttpUrl", () => {
  it("accepts absolute http and https URLs", () => {
    assert.equal(isHttpUrl("https://example.com/a.png"), true);
    assert.equal(isHttpUrl("http://example.com"), true);
  });

  it("rejects other schemes, missing hosts, and malformed input", () => {
    assert.equal(isHttpUrl("javascript:alert(1)"), false);
    assert.equal(isHttpUrl("ftp://example.com/x"), false);
    assert.equal(isHttpUrl("https://"), false);
    assert.equal(isHttpUrl("http:/example.com"), false);
    assert.equal(isHttpUrl("not a url"), false);
    assert.equal(isHttpUrl(""), false);
  });
});

describe("parseMinutes", () => {
  it("treats blank input as no value", () => {
    assert.deepEqual(parseMinutes(""), { ok: true, value: null });
    assert.deepEqual(parseMinutes("   "), { ok: true, value: null });
    assert.deepEqual(parseMinutes(undefined), { ok: true, value: null });
  });

  it("accepts whole numbers from 0 to the maximum", () => {
    assert.deepEqual(parseMinutes("0"), { ok: true, value: 0 });
    assert.deepEqual(parseMinutes(" 45 "), { ok: true, value: 45 });
    assert.deepEqual(parseMinutes(String(LIMITS.minutesMax)), {
      ok: true,
      value: LIMITS.minutesMax,
    });
  });

  it("rejects negative, fractional, non-numeric, and oversized durations", () => {
    for (const bad of ["-1", "1.5", "abc", "1e3", String(LIMITS.minutesMax + 1)]) {
      const result = parseMinutes(bad);
      assert.equal(result.ok, false, `expected ${bad} to be rejected`);
    }
  });
});

describe("parseTags", () => {
  it("lower-cases, trims, drops empties, and de-duplicates in order", () => {
    assert.deepEqual(parseTags(" Security, security ,, Onboarding "), {
      ok: true,
      value: ["security", "onboarding"],
    });
  });

  it("returns an empty list for blank input so updates can clear tags", () => {
    assert.deepEqual(parseTags(""), { ok: true, value: [] });
  });

  it("rejects more than the maximum number of distinct tags", () => {
    const many = Array.from({ length: LIMITS.tagCount + 1 }, (_, i) => `tag${i}`).join(",");
    const result = parseTags(many);
    assert.equal(result.ok, false);
    if (!result.ok) assert.ok(result.errors.tags);
  });

  it("rejects a tag longer than the maximum length", () => {
    const result = parseTags("x".repeat(LIMITS.tagLength + 1));
    assert.equal(result.ok, false);
  });
});

describe("validateCourseInput", () => {
  it("requires a title", () => {
    const result = validateCourseInput({ title: "   ", difficulty_level: "beginner" });
    assert.equal(result.ok, false);
    if (!result.ok) assert.ok(result.errors.title);
  });

  it("rejects over-long fields with a field-level error", () => {
    const result = validateCourseInput({
      ...validCourse,
      title: "t".repeat(LIMITS.title + 1),
      short_description: "s".repeat(LIMITS.shortDescription + 1),
    });
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.ok(result.errors.title);
      assert.ok(result.errors.short_description);
    }
  });

  it("rejects unsupported difficulty levels", () => {
    const result = validateCourseInput({ ...validCourse, difficulty_level: "expert" });
    assert.equal(result.ok, false);
    if (!result.ok) assert.ok(result.errors.difficulty_level);
  });

  it("maps blank optional fields to null so PATCH can clear them", () => {
    const result = validateCourseInput({
      title: "Course",
      short_description: "  ",
      description: "",
      category: "",
      difficulty_level: "advanced",
      estimated_minutes: "",
      thumbnail_url: "",
      tags: "",
    });
    assert.deepEqual(result, {
      ok: true,
      value: {
        title: "Course",
        short_description: null,
        description: null,
        category: null,
        difficulty_level: "advanced",
        estimated_minutes: null,
        thumbnail_url: null,
        tags: [],
      },
    });
  });

  it("validates thumbnail URLs against the http(s) rule", () => {
    const bad = validateCourseInput({ ...validCourse, thumbnail_url: "javascript:alert(1)" });
    assert.equal(bad.ok, false);
    if (!bad.ok) assert.ok(bad.errors.thumbnail_url);

    const good = validateCourseInput({
      ...validCourse,
      thumbnail_url: "https://example.com/cover.png",
    });
    assert.equal(good.ok, true);
    if (good.ok) assert.equal(good.value.thumbnail_url, "https://example.com/cover.png");
  });

  it("reports duration and tag errors together with other fields", () => {
    const result = validateCourseInput({
      title: "",
      estimated_minutes: "-5",
      tags: "x".repeat(LIMITS.tagLength + 1),
    });
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.ok(result.errors.title);
      assert.ok(result.errors.estimated_minutes);
      assert.ok(result.errors.tags);
    }
  });
});

describe("validateLessonInput", () => {
  it("accepts text lessons without content and treats blank content as null", () => {
    const result = validateLessonInput(
      { title: "Read", content_type: "text", content: "", description: "Overview" },
      true,
    );
    assert.deepEqual(result, {
      ok: true,
      value: {
        title: "Read",
        description: "Overview",
        content_type: "text",
        content: null,
        estimated_minutes: null,
        is_required: true,
      },
    });
  });

  it("requires a valid http(s) URL for video and external link lessons", () => {
    for (const content_type of ["video_url", "external_link"]) {
      const missing = validateLessonInput({ title: "L", content_type, content: "" }, true);
      assert.equal(missing.ok, false, `${content_type} should require content`);
      const bad = validateLessonInput({ title: "L", content_type, content: "not-a-url" }, true);
      assert.equal(bad.ok, false, `${content_type} should reject non-URL content`);
      const good = validateLessonInput(
        { title: "L", content_type, content: "https://example.com/x" },
        true,
      );
      assert.equal(good.ok, true, `${content_type} should accept https URL`);
    }
  });

  it("rejects legacy content types that the API no longer supports", () => {
    for (const content_type of ["video", "link", "file"]) {
      const result = validateLessonInput({ title: "L", content_type, content: "" }, true);
      assert.equal(result.ok, false, `${content_type} must be rejected`);
      if (!result.ok) assert.ok(result.errors.content_type);
    }
  });

  it("carries the required flag and rejects negative durations", () => {
    const optional = validateLessonInput({ title: "L", content_type: "text" }, false);
    assert.equal(optional.ok && optional.value.is_required, false);

    const negative = validateLessonInput(
      { title: "L", content_type: "text", estimated_minutes: "-2" },
      true,
    );
    assert.equal(negative.ok, false);
    if (!negative.ok) assert.ok(negative.errors.estimated_minutes);
  });

  it("requires a title", () => {
    const result = validateLessonInput({ title: "", content_type: "text" }, true);
    assert.equal(result.ok, false);
    if (!result.ok) assert.ok(result.errors.title);
  });
});
