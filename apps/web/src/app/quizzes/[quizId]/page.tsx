import { Suspense } from "react";

import { addQuestion, publishQuiz } from "@/app/actions";
import { apiGet } from "@/lib/api";
import type { AttemptSummary, QuizAuthorDetail, QuizLearnerDetail } from "@/lib/types";

import ActionForm from "../../components/action-form";
import { Field, inputClass } from "../../components/fields";
import QuizRunner from "../../components/quiz-runner";
import { AccessNotice, Card, EmptyState, PageHeader, StatusBadge } from "../../components/ui";

type QuizDetail = QuizAuthorDetail | QuizLearnerDetail;

function isAuthorDetail(quiz: QuizDetail): quiz is QuizAuthorDetail {
  return quiz.questions.length > 0 && "answer_key" in quiz.questions[0];
}

export default function QuizPage(props: PageProps<"/quizzes/[quizId]">) {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-8 py-12">
      <Suspense
        fallback={
          <p className="text-sm text-zinc-500" role="status">
            Loading quiz…
          </p>
        }
      >
        <QuizView params={props.params} />
      </Suspense>
    </main>
  );
}

async function QuizView({ params }: { params: Promise<{ quizId: string }> }) {
  const { quizId } = await params;
  const quizResult = await apiGet<QuizDetail>(`/quizzes/${quizId}`);

  if (!quizResult.ok) {
    return <AccessNotice kind={quizResult.kind} message={quizResult.message} />;
  }
  const quiz = quizResult.data;

  return (
    <>
      <PageHeader
        title={quiz.title}
        description={quiz.description ?? "No description provided."}
        action={<StatusBadge value={quiz.status} />}
      />

      {isAuthorDetail(quiz) ? (
        <QuizAuthorDetailSection quiz={quiz} />
      ) : (
        <section className="flex flex-col gap-6">
          {quiz.questions.length === 0 ? (
            <EmptyState
              title="No questions yet"
              description="This quiz does not have any questions yet."
            />
          ) : (
            <QuizRunner quiz={quiz} />
          )}
          <Suspense fallback={null}>
            <AttemptHistory quizId={quiz.id} />
          </Suspense>
        </section>
      )}
    </>
  );
}

async function AttemptHistory({ quizId }: { quizId: string }) {
  const result = await apiGet<AttemptSummary[]>(`/quizzes/${quizId}/results`);
  if (!result.ok || result.data.length === 0) {
    return null;
  }
  return (
    <Card title="Your attempts">
      <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
        {result.data.map((attempt) => (
          <li key={attempt.id} className="flex items-center justify-between py-2">
            <span>Attempt #{attempt.attempt_number}</span>
            <span className="text-zinc-500">
              {attempt.status}
              {attempt.score !== null ? ` · ${attempt.score}%` : ""}
              {attempt.passed === true ? " · passed" : attempt.passed === false ? " · failed" : ""}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function QuizAuthorDetailSection({ quiz }: { quiz: QuizAuthorDetail }) {
  return (
    <>
      <div className="flex flex-wrap gap-3">
        <ActionForm action={publishQuiz} submitLabel="Publish quiz">
          <input type="hidden" name="quiz_id" value={quiz.id} />
        </ActionForm>
      </div>

      <Card title="Add question">
        <ActionForm action={addQuestion} submitLabel="Add question">
          <input type="hidden" name="quiz_id" value={quiz.id} />
          <Field label="Question type">
            <select name="question_type" defaultValue="single_choice" className={inputClass}>
              <option value="single_choice">Single choice</option>
              <option value="multiple_choice">Multiple choice</option>
              <option value="true_false">True / false</option>
            </select>
          </Field>
          <Field label="Prompt">
            <textarea name="prompt" required rows={2} className={inputClass} />
          </Field>
          <Field label="Options (one per line, id=text)">
            <textarea
              name="options"
              required
              rows={4}
              placeholder={"a=First option\nb=Second option"}
              className={inputClass}
            />
          </Field>
          <Field label="Answer key (comma-separated option ids)">
            <input name="answer_key" required placeholder="a" className={inputClass} />
          </Field>
          <Field label="Explanation">
            <textarea name="explanation" rows={2} className={inputClass} />
          </Field>
          <Field label="Points">
            <input name="points" type="number" min={1} defaultValue={1} className={inputClass} />
          </Field>
        </ActionForm>
      </Card>

      {quiz.questions.length === 0 ? (
        <EmptyState
          title="No questions yet"
          description="Add at least one question before publishing."
        />
      ) : (
        <ul className="flex flex-col gap-4">
          {quiz.questions.map((question) => (
            <li key={question.id}>
              <Card
                title={question.prompt}
                meta={
                  <span className="text-xs text-zinc-500">
                    {question.question_type} · {question.points} pt
                  </span>
                }
              >
                <ul className="flex flex-col gap-1">
                  {question.options.map((option) => (
                    <li key={option.id} className="flex items-center gap-2">
                      <span className="font-mono text-xs text-zinc-400">{option.id}</span>
                      <span
                        className={
                          question.answer_key.includes(option.id)
                            ? "font-medium text-green-700 dark:text-green-400"
                            : ""
                        }
                      >
                        {option.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
