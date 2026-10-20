export interface FormState {
  status: "idle" | "success" | "error";
  message: string;
  /** Field-level validation messages keyed by input name. */
  fieldErrors?: Record<string, string>;
}

export const initialFormState: FormState = { status: "idle", message: "" };

export type FormAction = (state: FormState, formData: FormData) => Promise<FormState>;
