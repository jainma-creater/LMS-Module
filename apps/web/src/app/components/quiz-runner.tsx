"use client";

import { useState, useTransition } from "react";

import { beginAttempt, completeAttempt } from "@/app/actions";
import type { AttemptResult, AttemptStart, QuizLearnerDetail } from "@/lib/types";

function isMulti(questionType: string): boolean {
  return questionType === "multiple_choice";
}

export default function QuizRunner({ quiz }: { quiz: QuizLearnerDetail }) {
  const [attempt, setAttempt] = useState<AttemptStart | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [selected, setSelected] = useState<Record<string, string[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function start() {
    setError(null);
    setResult(null);
    startTransition(async () => {
      const response = await beginAttempt(quiz.id);
      if (response.ok) {
        setAttempt(response.data);
        setSelected({});
      } else {
        setError(response.message);
      }
    });
  }

  function toggle(questionId: string, optionId: string, multi: boolean) {
    setSelected((current) => {
      const existing = current[questionId] ?? [];
      if (multi) {
        const next = existing.includes(optionId)
          ? existing.filter((value) => value !== optionId)
          : [...existing, optionId];
        return { ...current, [questionId]: next };
      }
      return { ...current, [questionId]: [optionId] };
    });
  }

  function submit() {
    if (!attempt) return;
    setError(null);
    const answers = attempt.questions.map((question) => ({
      question_id: question.id,
      selected: selected[question.id] ?? [],
    }));
    startTransition(async () => {
      const response = await completeAttempt(quiz.id, attempt.attempt_id, answers);
      if (response.ok) {
        setResult(response.data);
        setAttempt(null);
      } else {
        setError(response.message);
      }
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
        <span>Pass score: {quiz.pass_score}%</span>
        <span>
          Attempt limit: {quiz.attempt_limit ?? "unlimited"}
        </span>
      </div>

      {error ? (
        <p role="alert" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="flex flex-col gap-4 rounded-lg border border-zinc-200 p-5 dark:border-zinc-800">
          <p className="text-lg font-medium">
            Score: {result.score ?? 0}% — {result.passed ? "Passed" : "Not passed"}
          </p>
          <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
            {result.results.map((item) => (
              <li key={item.question_id} className="py-2 text-sm">
                <span className={item.is_correct ? "text-green-700 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                  {item.is_correct ? "Correct" : "Incorrect"}
                </span>
                <span className="ml-2 text-zinc-500">
                  {item.points_awarded} point{item.points_awarded === 1 ? "" : "s"}
                </span>
                {item.explanation ? (
                  <p className="mt-1 text-zinc-600 dark:text-zinc-400">{item.explanation}</p>
                ) : null}
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={start}
            disabled={pending}
            className="self-start rounded-md bg-black px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-black"
          >
            Start another attempt
          </button>
        </div>
      ) : attempt ? (
        <div className="flex flex-col gap-5">
          <p className="text-sm text-zinc-500">
            Attempt #{attempt.attempt_number} started.
          </p>
          {attempt.questions.map((question) => {
            const multi = isMulti(question.question_type);
            return (
              <fieldset
                key={question.id}
                className="flex flex-col gap-2 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
              >
                <legend className="px-1 text-sm font-medium">{question.prompt}</legend>
                <p className="text-xs text-zinc-400">
                  {question.points} point{question.points === 1 ? "" : "s"}
                  {multi ? " · select all that apply" : ""}
                </p>
                {question.options.map((option) => {
                  const checked = (selected[question.id] ?? []).includes(option.id);
                  return (
                    <label key={option.id} className="flex items-center gap-2 text-sm">
                      <input
                        type={multi ? "checkbox" : "radio"}
                        name={question.id}
                        checked={checked}
                        onChange={() => toggle(question.id, option.id, multi)}
                      />
                      <span>{option.text}</span>
                    </label>
                  );
                })}
              </fieldset>
            );
          })}
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="self-start rounded-md bg-black px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-black"
          >
            {pending ? "Submitting…" : "Submit attempt"}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={start}
          disabled={pending}
          className="self-start rounded-md bg-black px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-black"
        >
          {pending ? "Starting…" : "Start attempt"}
        </button>
      )}
    </div>
  );
}
