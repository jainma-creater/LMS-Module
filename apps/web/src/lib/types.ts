export type CourseStatus = "draft" | "published" | "archived";

export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

export type LessonContentType = "text" | "video_url" | "external_link";

export type EnrollmentStatus = "assigned" | "in_progress" | "completed";

export type AssignmentSource = "manager" | "self" | "system";

export type QuestionType = "single_choice" | "multiple_choice" | "true_false";

export type LearnerStatus = "active" | "inactive";

export type GroupStatus = "active" | "inactive";

export type GroupKind = "team" | "department" | "organization" | string;

export type AssignmentStatus = "active" | "cancelled";

export type DerivedAssignmentStatus =
  | "awaiting_account"
  | "assigned"
  | "in_progress"
  | "completed"
  | "withdrawn"
  | "cancelled";

export interface CourseSummary {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  category: string | null;
  difficulty_level: string;
  status: string;
}

export interface CourseCounts {
  modules: number;
  lessons: number;
}

export interface CourseDetail extends CourseSummary {
  short_description: string | null;
  estimated_minutes: number | null;
  thumbnail_url: string | null;
  tags: string[];
  owner_id: string | null;
  version: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  counts: CourseCounts;
}

/** Full course as returned by the authoring endpoints (CourseResponse). */
export interface CourseRecord {
  id: string;
  title: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  category: string | null;
  difficulty_level: string;
  estimated_minutes: number | null;
  thumbnail_url: string | null;
  tags: string[];
  status: string;
  owner_id: string | null;
  version: number;
  published_at: string | null;
}

export interface CatalogCourse {
  id: string;
  title: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  category: string | null;
  difficulty_level: string;
  estimated_minutes: number | null;
  thumbnail_url: string | null;
  tags: string[];
  version: number;
}

export interface CoursePage {
  items: CatalogCourse[];
  total: number;
  limit: number;
  offset: number;
}

export interface CatalogCourseDetail extends CatalogCourse {
  status: string;
  owner_id: string | null;
  published_at: string | null;
  counts: CourseCounts;
}

export interface Lesson {
  id: string;
  module_id: string;
  title: string;
  description: string | null;
  content_type: LessonContentType;
  content: string | null;
  sort_order: number;
  estimated_minutes: number | null;
  is_required: boolean;
}

export interface Module {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  sort_order: number;
}

export interface ModuleWithLessons extends Module {
  lessons: Lesson[];
}

export interface CourseContent {
  course: CourseSummary;
  modules: ModuleWithLessons[];
}

export interface Enrollment {
  id: string;
  learner_id: string;
  course_id: string;
  assignment_source: string;
  assigned_by: string | null;
  assigned_at: string;
  due_at: string | null;
  status: string;
  completed_at: string | null;
  overdue: boolean;
}

export interface ProgressSummary {
  required_lessons: number;
  completed_lessons: number;
  percent: number;
  is_complete: boolean;
}

export interface MyLearningItem {
  enrollment: Enrollment;
  course: CourseSummary;
  progress: ProgressSummary;
}

export interface LessonProgress {
  lesson_id: string;
  status: string;
  last_position: number | null;
  completed_at: string | null;
}

export interface CourseProgress {
  course_id: string;
  required_lessons: number;
  completed_lessons: number;
  percent: number;
  is_complete: boolean;
  lessons: LessonProgress[];
}

export interface CompletionItem {
  course_id: string;
  course_title: string;
  completed_at: string;
  completion_rule_version: number;
}

export interface QuizOption {
  id: string;
  text: string;
}

export interface Quiz {
  id: string;
  course_id: string | null;
  lesson_id: string | null;
  title: string;
  description: string | null;
  pass_score: number;
  attempt_limit: number | null;
  status: string;
}

export interface LearnerQuestion {
  id: string;
  question_type: string;
  prompt: string;
  options: QuizOption[];
  sort_order: number;
  points: number;
}

export interface AuthorQuestion extends LearnerQuestion {
  quiz_id: string;
  answer_key: string[];
  explanation: string | null;
}

export interface QuizLearnerDetail extends Quiz {
  questions: LearnerQuestion[];
}

export interface QuizAuthorDetail extends Quiz {
  questions: AuthorQuestion[];
}

export interface AttemptStart {
  attempt_id: string;
  quiz_id: string;
  attempt_number: number;
  status: string;
  started_at: string;
  questions: LearnerQuestion[];
}

export interface AttemptResult {
  attempt_id: string;
  quiz_id: string;
  attempt_number: number;
  status: string;
  score: number | null;
  passed: boolean | null;
  started_at: string;
  submitted_at: string | null;
  results: {
    question_id: string;
    selected: string[];
    is_correct: boolean;
    points_awarded: number;
    explanation: string | null;
  }[];
}

export interface AttemptSummary {
  id: string;
  quiz_id: string;
  attempt_number: number;
  status: string;
  score: number | null;
  passed: boolean | null;
  started_at: string;
  submitted_at: string | null;
}

export interface Learner {
  id: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  department: string | null;
  business_unit: string | null;
  status: LearnerStatus;
  user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearnerPage {
  items: Learner[];
  total: number;
  limit: number;
  offset: number;
}

export interface LearningGroup {
  id: string;
  name: string;
  description: string | null;
  kind: string;
  status: GroupStatus;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface GroupPage {
  items: LearningGroup[];
  total: number;
  limit: number;
  offset: number;
}

export interface GroupMember {
  membership_id: string;
  learner_id: string;
  employee_id: string;
  full_name: string;
  email: string;
  learner_status: string;
  added_at: string;
  removed_at: string | null;
}

export interface MemberPage {
  items: GroupMember[];
  total: number;
  limit: number;
  offset: number;
}

export interface AssignmentView {
  id: string;
  course_id: string;
  course_title: string;
  learner_id: string;
  learner_employee_id: string;
  learner_name: string;
  group_assignment_id: string | null;
  group_id: string | null;
  group_name: string | null;
  source: string;
  status: string;
  derived_status: DerivedAssignmentStatus;
  enrollment_id: string | null;
  due_at: string | null;
  overdue: boolean;
  assigned_at: string;
  cancelled_at: string | null;
  cancel_reason: string | null;
}

export interface AssignmentPage {
  items: AssignmentView[];
  total: number;
  limit: number;
  offset: number;
}

export interface GroupAssignmentView {
  id: string;
  course_id: string;
  course_title: string;
  group_id: string;
  group_name: string;
  status: string;
  due_at: string | null;
  assigned_at: string;
  cancelled_at: string | null;
  cancel_reason: string | null;
}

export interface GroupAssignmentPage {
  items: GroupAssignmentView[];
  total: number;
  limit: number;
  offset: number;
}

export interface GroupAssignmentResult {
  group_assignment: GroupAssignmentView;
  created: number;
  skipped_existing: number;
  skipped_inactive: number;
}

export interface EnrollmentResponse {
  id: string;
  learner_id: string;
  course_id: string;
  assignment_source: string;
  assigned_by: string | null;
  assigned_at: string;
  due_at: string | null;
  status: string;
  completed_at: string | null;
  overdue: boolean;
}

export interface AssignmentDetail extends AssignmentView {
  enrollment: EnrollmentResponse | null;
  progress: ProgressSummary | null;
}

export interface StoryboardScene {
  scene_number: number;
  title: string;
  narration: string;
  visual_prompt: string;
  duration_sec: number;
}

export interface LessonDraft {
  title: string;
  description: string;
  content_type: string;
  content: string;
  estimated_minutes: number;
  is_required: boolean;
}

export interface ModuleDraft {
  title: string;
  description: string;
  lessons: LessonDraft[];
}

export interface CourseDraft {
  title: string;
  short_description: string;
  description: string;
  category: string;
  difficulty_level: string;
  learning_objectives: string[];
  key_takeaways: string[];
  tags: string[];
  is_mandatory: boolean;
  validity_days: number | null;
  modules: ModuleDraft[];
  storyboard: StoryboardScene[];
  captions_vtt: string | null;
}

// Mirrors backend QuestionOption. Correctness is stored in QuizQuestionDraft.answer_key (option ids).
export interface QuizOptionDraft {
  id: string;
  text: string;
}

export interface QuizQuestionDraft {
  prompt: string;
  question_type: string;
  options: QuizOptionDraft[];
  answer_key: string[];
  explanation: string;
  difficulty: string;
}

export interface QuizDraft {
  pass_score: number;
  attempt_limit: number;
  questions: QuizQuestionDraft[];
}

export interface TrainingGenerationJob {
  id: string;
  title: string;
  topic: string | null;
  source_file_name: string | null;
  language: string;
  target_duration_minutes: number;
  audience: string;
  include_quiz: boolean;
  include_video: boolean;
  status: "pending" | "processing" | "generated" | "published" | "failed";
  progress_percent: number;
  stage: string;
  error_message: string | null;
  retry_count: number;
  generated_course_data: CourseDraft | null;
  generated_quiz_data: QuizDraft | null;
  generated_video_asset_url: string | null;
  generated_video_duration_seconds: number | null;
  published_course_id: string | null;
  published_quiz_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PublishDraftResult {
  job_id: string;
  course_id: string;
  course_slug: string;
  quiz_id: string | null;
  assignment_id: string | null;
  group_assignment_id: string | null;
  message: string;
}
