"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import {
  generateTrainingDraft,
  publishTrainingDraft,
  regenerateQuizQuestion,
  updateTrainingDraft,
} from "@/app/actions";
import type {
  CourseDraft,
  LearningGroup,
  PublishDraftResult,
  QuizDraft,
  TrainingGenerationJob,
} from "@/lib/types";

interface StudioClientProps {
  groups: LearningGroup[];
}

export default function StudioClient({ groups }: StudioClientProps) {
  // Step 1: Configuration & Input
  const [mode, setMode] = useState<"topic" | "document">("topic");
  const [topic, setTopic] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("en");
  const [duration, setDuration] = useState("10");
  const [audience, setAudience] = useState("All Employees");
  const [includeQuiz, setIncludeQuiz] = useState(true);
  const [includeVideo, setIncludeVideo] = useState(true);

  // Workflow State
  const [job, setJob] = useState<TrainingGenerationJob | null>(null);
  const [courseDraft, setCourseDraft] = useState<CourseDraft | null>(null);
  const [quizDraft, setQuizDraft] = useState<QuizDraft | null>(null);
  const [publishedResult, setPublishedResult] = useState<PublishDraftResult | null>(null);

  // Status / Feedback
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Question Regeneration inline state
  const [regenIdx, setRegenIdx] = useState<number | null>(null);
  const [regenHint, setRegenHint] = useState("");

  // Publish Dialog state
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [dueDays, setDueDays] = useState("30");

  // Step 1: Submit Generation
  function handleGenerate(e?: React.FormEvent, directTopic?: string) {
    if (e) {
      e.preventDefault();
    }
    setError(null);
    setInfo(null);

    const chosenTopic = (directTopic || topic).trim();

    if (mode === "topic" && !chosenTopic) {
      const fallbackTopic = "Cybersecurity Best Practices";
      setTopic(fallbackTopic);
      executeGeneration(fallbackTopic);
      return;
    }

    if (mode === "document" && !selectedFile) {
      setError("Please select a document file (.pdf, .docx, .pptx, .txt).");
      return;
    }

    executeGeneration(chosenTopic);
  }

  function executeGeneration(activeTopic: string) {
    startTransition(async () => {
      try {
        let res;
        if (mode === "topic" || (!selectedFile && activeTopic)) {
          res = await generateTrainingDraft({
            topic: activeTopic,
            language,
            target_duration_minutes: parseInt(duration, 10) || 10,
            audience,
            include_quiz: includeQuiz,
            include_video: includeVideo,
          });
        } else {
          const formData = new FormData();
          if (selectedFile) {
            formData.append("file", selectedFile);
          }
          if (activeTopic) {
            formData.append("topic", activeTopic);
          }
          formData.append("language", language);
          formData.append("target_duration_minutes", duration);
          formData.append("audience", audience);
          formData.append("include_quiz", includeQuiz ? "true" : "false");
          formData.append("include_video", includeVideo ? "true" : "false");
          res = await generateTrainingDraft(formData);
        }

        if (res.ok) {
          setJob(res.data);
          setCourseDraft(res.data.generated_course_data);
          setQuizDraft(res.data.generated_quiz_data);
          setInfo("Draft generated successfully. Review and edit below before publishing.");
        } else {
          setError(res.message);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to generate training draft.");
      }
    });
  }

  // Save Draft Edits
  function handleSaveDraft() {
    if (!job || !courseDraft) return;
    setError(null);
    setInfo(null);

    startTransition(async () => {
      const res = await updateTrainingDraft(job.id, courseDraft, quizDraft);
      if (res.ok) {
        setJob(res.data);
        setCourseDraft(res.data.generated_course_data);
        setQuizDraft(res.data.generated_quiz_data);
        setInfo("Draft changes saved successfully.");
      } else {
        setError(res.message);
      }
    });
  }

  // Regenerate Single Question
  function handleRegenerateQuestion(index: number) {
    if (!job) return;
    setError(null);
    setInfo(null);

    startTransition(async () => {
      const res = await regenerateQuizQuestion(job.id, index, regenHint);
      if (res.ok) {
        if (quizDraft) {
          const nextQuestions = [...quizDraft.questions];
          nextQuestions[index] = res.data;
          setQuizDraft({ ...quizDraft, questions: nextQuestions });
        }
        setRegenIdx(null);
        setRegenHint("");
        setInfo(`Question #${index + 1} regenerated successfully.`);
      } else {
        setError(res.message);
      }
    });
  }

  // Publish Draft
  function handleConfirmPublish() {
    if (!job) return;
    setError(null);
    setInfo(null);

    startTransition(async () => {
      const res = await publishTrainingDraft(job.id, {
        assign_to_group_id: selectedGroupId || null,
        due_days: dueDays ? Number.parseInt(dueDays, 10) : null,
      });

      if (res.ok) {
        setPublishedResult(res.data);
        setShowPublishModal(false);
      } else {
        setError(res.message);
      }
    });
  }

  // Reset to create another course
  function handleReset() {
    setJob(null);
    setCourseDraft(null);
    setQuizDraft(null);
    setPublishedResult(null);
    setTopic("");
    setSelectedFile(null);
    setError(null);
    setInfo(null);
  }

  // -------------------------------------------------------------------------
  // RENDER: Published Confirmation
  // -------------------------------------------------------------------------
  if (publishedResult) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-8 dark:border-emerald-900/50 dark:bg-emerald-950/20">
        <div className="flex items-center gap-3 text-emerald-800 dark:text-emerald-300">
          <svg className="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <h2 className="text-xl font-bold">Training Published Successfully!</h2>
        </div>
        <p className="mt-2 text-sm text-emerald-700 dark:text-emerald-400">
          {publishedResult.message}
        </p>

        <div className="mt-6 flex flex-wrap gap-4">
          <Link
            href={`/courses/${publishedResult.course_slug}`}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
          >
            View in Catalog →
          </Link>
          <Link
            href={`/manage/${publishedResult.course_id}`}
            className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
          >
            Manage Course Curriculum
          </Link>
          {publishedResult.quiz_id && (
            <Link
              href={`/quizzes/${publishedResult.quiz_id}`}
              className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
            >
              Take Assessment Quiz
            </Link>
          )}
          <button
            type="button"
            onClick={handleReset}
            className="rounded-lg px-4 py-2 text-sm text-zinc-600 hover:underline dark:text-zinc-400"
          >
            Create Another Course
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // RENDER: Main Studio View
  // -------------------------------------------------------------------------
  return (
    <div className="flex flex-col gap-8">
      {/* Messages */}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </div>
      )}
      {info && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-200">
          {info}
        </div>
      )}

      {/* Step 1: Input & Configuration Form (Visible when not yet generated or collapsed) */}
      {!job && (
        <div
          className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-4 dark:border-zinc-800">
            <div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
                1. Select Training Source & Configure
              </h2>
              <p className="text-xs text-zinc-500">
                Provide an approved policy document or a topic. Our guided pipeline produces the syllabus, video, and quiz.
              </p>
            </div>
            <div className="flex rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
              <button
                type="button"
                onClick={() => setMode("topic")}
                className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                  mode === "topic"
                    ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-white"
                    : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
                }`}
              >
                Topic
              </button>
              <button
                type="button"
                onClick={() => setMode("document")}
                className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                  mode === "document"
                    ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-white"
                    : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
                }`}
              >
                Upload Document
              </button>
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-6">
            {mode === "topic" ? (
              <div>
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Training Topic or Title
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Enterprise Phishing Defense & Incident Escalation"
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
                <div className="mt-2.5 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                  <span className="font-medium text-zinc-600 dark:text-zinc-400">Quick prompts:</span>
                  {[
                    "Cybersecurity Best Practices",
                    "Code of Conduct & Anti-Bribery",
                    "Workplace Incident Escalation",
                    "Customer Privacy & Data Protection",
                  ].map((p) => {
                    const isSelected = topic === p;
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => {
                          setMode("topic");
                          setTopic(p);
                          setError(null);
                        }}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                          isSelected
                            ? "bg-blue-600 text-white shadow-xs"
                            : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                        }`}
                      >
                        {p}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Source Document (.pdf, .docx, .pptx, .txt)
                </label>
                <input
                  type="file"
                  accept=".pdf,.docx,.pptx,.txt,.md"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="mt-1 block w-full text-sm text-zinc-500 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-950 dark:file:text-blue-300"
                />
                <p className="mt-1 text-xs text-zinc-500">
                  Text will be parsed and used to ground all lesson outlines, explanations, and questions.
                </p>
                {selectedFile && (
                  <p className="mt-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>
            )}

            {/* Target Settings */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="en">English (US)</option>
                  <option value="es">Spanish (Español)</option>
                  <option value="fr">French (Français)</option>
                  <option value="de">German (Deutsch)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Target Duration
                </label>
                <select
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="5">5 Minutes (Micro-learning)</option>
                  <option value="10">10 Minutes (Standard)</option>
                  <option value="15">15 Minutes (Comprehensive)</option>
                  <option value="30">30 Minutes (Deep Dive)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Target Audience
                </label>
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="All Employees">All Employees</option>
                  <option value="Software Engineering">Software Engineering</option>
                  <option value="Sales & Customer Success">Sales & Customer Success</option>
                  <option value="Operations & IT">Operations & IT</option>
                  <option value="People & Leadership">People & Leadership</option>
                </select>
              </div>
            </div>

            {/* Feature Toggles */}
            <div className="flex flex-wrap gap-6 border-t border-zinc-100 pt-4 dark:border-zinc-800">
              <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                <input
                  type="checkbox"
                  checked={includeQuiz}
                  onChange={(e) => setIncludeQuiz(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                />
                Include Assessment Quiz (Objective questions & answer keys)
              </label>
              <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                <input
                  type="checkbox"
                  checked={includeVideo}
                  onChange={(e) => setIncludeVideo(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                />
                Generate Video Narration & Subtitles
              </label>
            </div>

            {/* Action Button */}
            <div className="flex items-center justify-end">
              <button
                type="button"
                onClick={() => handleGenerate()}
                disabled={isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {isPending ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Generating Training Draft…
                  </>
                ) : (
                  <>
                    <span>⚡ Generate Training Draft (1-Click)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Draft Review, Video Preview, Quiz Review, and Publishing */}
      {job && courseDraft && (
        <div className="flex flex-col gap-8">
          {/* Draft Status Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50/80 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                  Draft Mode (Unpublished)
                </span>
                <span className="text-xs text-zinc-500">Job #{job.id.slice(0, 8)}</span>
              </div>
              <h3 className="mt-1 text-base font-bold text-zinc-900 dark:text-zinc-50">
                {courseDraft.title}
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400">
                Review and edit content. Generated training is never published automatically without your explicit approval.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={isPending}
                className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-sm hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
              >
                Save Draft Changes
              </button>
              <button
                type="button"
                onClick={() => setShowPublishModal(true)}
                disabled={isPending}
                className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                Approve & Publish →
              </button>
            </div>
          </div>

          {/* Section A: Course Overview & Metadata */}
          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Course Details & Objectives
            </h3>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                  Course Title
                </label>
                <input
                  type="text"
                  value={courseDraft.title}
                  onChange={(e) => setCourseDraft({ ...courseDraft, title: e.target.value })}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                  Category
                </label>
                <input
                  type="text"
                  value={courseDraft.category}
                  onChange={(e) => setCourseDraft({ ...courseDraft, category: e.target.value })}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                  Summary Description
                </label>
                <textarea
                  rows={2}
                  value={courseDraft.short_description}
                  onChange={(e) =>
                    setCourseDraft({ ...courseDraft, short_description: e.target.value })
                  }
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
              </div>
            </div>

            {/* Learning Objectives & Key Takeaways */}
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
                <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Learning Objectives:
                </span>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
                  {courseDraft.learning_objectives.map((obj, i) => (
                    <li key={i}>{obj}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
                <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Key Takeaways:
                </span>
                <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
                  {courseDraft.key_takeaways.map((takeaway, i) => (
                    <li key={i}>{takeaway}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Section B: Video Player & Storyboard Preview */}
          {courseDraft.storyboard && courseDraft.storyboard.length > 0 && (
            <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3 dark:border-zinc-800">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    Video Storyboard & Narration Preview
                  </h3>
                  <p className="text-xs text-zinc-500">
                    Generated scene narration, visual prompts, and synchronized WebVTT captions.
                  </p>
                </div>
                {job.generated_video_duration_seconds && (
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                    Duration: ~{job.generated_video_duration_seconds}s
                  </span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* HTML5 Video Player */}
                <div>
                  {job.generated_video_asset_url ? (
                    <div className="overflow-hidden rounded-lg bg-black shadow">
                      <video
                        controls
                        className="w-full"
                        src={`/api/studio/video-asset/${job.generated_video_asset_url.split("/").pop()}`}
                      >
                        <track
                          kind="subtitles"
                          src={`/api/studio/captions/${job.id}`}
                          srcLang="en"
                          label="English"
                          default
                        />
                        Your browser does not support HTML5 video playback.
                      </video>
                    </div>
                  ) : (
                    <div className="flex h-48 items-center justify-center rounded-lg bg-zinc-100 text-xs text-zinc-500 dark:bg-zinc-800">
                      Video rendering skipped.
                    </div>
                  )}
                  <p className="mt-2 text-center text-xs text-zinc-500">
                    Player preview with synchronized WebVTT subtitles
                  </p>
                </div>

                {/* Storyboard Scenes List */}
                <div className="flex max-h-72 flex-col gap-3 overflow-y-auto pr-1">
                  {courseDraft.storyboard.map((scene) => (
                    <div
                      key={scene.scene_number}
                      className="rounded-lg border border-zinc-200 p-3 text-xs dark:border-zinc-800"
                    >
                      <div className="flex items-center justify-between font-semibold text-zinc-800 dark:text-zinc-200">
                        <span>
                          Scene {scene.scene_number}: {scene.title}
                        </span>
                        <span className="text-zinc-500">{scene.duration_sec}s</span>
                      </div>
                      <p className="mt-1 text-zinc-600 dark:text-zinc-300">
                        <span className="font-medium text-zinc-700 dark:text-zinc-200">
                          Narration:{" "}
                        </span>
                        {scene.narration}
                      </p>
                      <p className="mt-1 italic text-zinc-500">
                        <span className="font-medium not-italic text-zinc-700 dark:text-zinc-400">
                          Visual:{" "}
                        </span>
                        {scene.visual_prompt}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Section C: Modules and Lessons Outline */}
          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Module Curriculum & Lessons ({courseDraft.modules.length} Modules)
            </h3>
            <div className="mt-4 flex flex-col gap-4">
              {courseDraft.modules.map((mod, modIdx) => (
                <div
                  key={modIdx}
                  className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
                >
                  <div className="font-medium text-zinc-900 dark:text-zinc-100">
                    {mod.title}
                  </div>
                  <div className="mt-3 flex flex-col gap-3">
                    {mod.lessons.map((lesson, lessonIdx) => (
                      <div
                        key={lessonIdx}
                        className="rounded-md bg-zinc-50 p-3 text-xs dark:bg-zinc-800/60"
                      >
                        <div className="flex items-center justify-between font-medium text-zinc-800 dark:text-zinc-200">
                          <span>
                            Lesson {lessonIdx + 1}: {lesson.title}
                          </span>
                          <span className="text-zinc-500">~{lesson.estimated_minutes} min</span>
                        </div>
                        <p className="mt-1 text-zinc-500">{lesson.description}</p>
                        <div className="mt-2 rounded bg-white p-2 font-mono text-[11px] text-zinc-700 shadow-sm dark:bg-zinc-900 dark:text-zinc-300">
                          {lesson.content.slice(0, 160)}…
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section D: Assessment Quiz Review & Single-Question Regeneration */}
          {quizDraft && (
            <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3 dark:border-zinc-800">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                    Assessment Quiz ({quizDraft.questions.length} Questions)
                  </h3>
                  <p className="text-xs text-zinc-500">
                    Passing Score: {quizDraft.pass_score}% · Attempt Limit: {quizDraft.attempt_limit}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-col gap-4">
                {quizDraft.questions.map((q, qIdx) => (
                  <div
                    key={qIdx}
                    className="rounded-lg border border-zinc-200 p-4 text-xs dark:border-zinc-800"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">
                          Q{qIdx + 1}. {q.prompt}
                        </span>
                        <div className="mt-1 text-[11px] text-zinc-500">
                          Type: {q.question_type} · Difficulty: {q.difficulty}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          setRegenIdx(qIdx);
                          setRegenHint("");
                        }}
                        className="rounded border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300"
                      >
                        ↻ Regenerate Question
                      </button>
                    </div>

                    {/* Inline Regeneration Prompt */}
                    {regenIdx === qIdx && (
                      <div className="mt-3 rounded-md bg-blue-50/70 p-3 dark:bg-blue-950/40">
                        <label className="block text-[11px] font-medium text-blue-900 dark:text-blue-200">
                          Topic hint or focus (optional):
                        </label>
                        <div className="mt-1 flex gap-2">
                          <input
                            type="text"
                            value={regenHint}
                            onChange={(e) => setRegenHint(e.target.value)}
                            placeholder="e.g. Focus on penalty thresholds or reporting deadlines"
                            className="w-full rounded border border-blue-300 px-2 py-1 text-xs dark:border-blue-800 dark:bg-zinc-900 dark:text-white"
                          />
                          <button
                            type="button"
                            onClick={() => handleRegenerateQuestion(qIdx)}
                            disabled={isPending}
                            className="rounded bg-blue-600 px-3 py-1 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                          >
                            Regenerate
                          </button>
                          <button
                            type="button"
                            onClick={() => setRegenIdx(null)}
                            className="rounded px-2 text-zinc-500 hover:underline"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Options list */}
                    <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {q.options.map((opt, optIdx) => {
                        // answer_key holds option ids; the backend option has no is_correct flag.
                        const isCorrect = q.answer_key.includes(opt.id);
                        return (
                          <div
                            key={opt.id || optIdx}
                            className={`rounded border p-2 ${
                              isCorrect
                                ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
                                : "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-800/40 dark:text-zinc-300"
                            }`}
                          >
                            <span className="font-semibold">{String.fromCharCode(65 + optIdx)}. </span>
                            {opt.text}
                            {isCorrect && (
                              <span className="ml-2 font-bold text-emerald-600 dark:text-emerald-400">
                                ✓ Correct
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Explanation */}
                    <div className="mt-2 text-zinc-500">
                      <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                        Explanation:{" "}
                      </span>
                      {q.explanation}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bottom Action Bar */}
          <div className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"
            >
              ← Discard & Start Over
            </button>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={isPending}
                className="rounded-lg border border-zinc-300 px-4 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-200"
              >
                Save Changes to Draft
              </button>
              <button
                type="button"
                onClick={() => setShowPublishModal(true)}
                disabled={isPending}
                className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                Approve & Publish Training →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* Publish & Assign Modal Dialog */}
      {/* --------------------------------------------------------------------- */}
      {showPublishModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Approve & Publish Training
            </h3>
            <p className="mt-1 text-xs text-zinc-500">
              This will create a published course, activate the assessment quiz, and optionally assign it immediately to employees.
            </p>

            <div className="mt-4 flex flex-col gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Assign to Learning Group (Optional)
                </label>
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                >
                  <option value="">None (Publish to catalog only)</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name} ({g.kind})
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-[11px] text-zinc-500">
                  All active members of this group will receive automatic course enrollments.
                </p>
              </div>

              {selectedGroupId && (
                <div>
                  <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    Completion Due Date (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={dueDays}
                    onChange={(e) => setDueDays(e.target.value)}
                    className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                  />
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
              <button
                type="button"
                onClick={() => setShowPublishModal(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmPublish}
                disabled={isPending}
                className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                {isPending ? "Publishing…" : "Confirm & Publish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
