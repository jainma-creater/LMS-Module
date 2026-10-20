"use client";

import { useState } from "react";

import { updateLearner } from "@/app/actions";
import type { Learner, LearnerStatus } from "@/lib/types";

import { AuthoringForm, SelectField, TextField } from "./authoring-form";

export default function LearnerForm({ learner }: { learner: Learner }) {
  const [status, setStatus] = useState<LearnerStatus>(learner.status);

  return (
    <AuthoringForm
      action={updateLearner}
      idPrefix={`learner-${learner.id}`}
      submitLabel="Save changes"
      pendingLabel="Saving…"
    >
      <input type="hidden" name="learner_id" value={learner.id} />

      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          name="employee_id"
          label="Employee ID"
          required
          maxLength={64}
          defaultValue={learner.employee_id}
        />
        <SelectField
          name="status"
          label="Status"
          options={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
          defaultValue={status}
          onChange={(v) => setStatus(v as LearnerStatus)}
        />
        <TextField
          name="first_name"
          label="First name"
          required
          maxLength={100}
          defaultValue={learner.first_name}
        />
        <TextField
          name="last_name"
          label="Last name"
          required
          maxLength={100}
          defaultValue={learner.last_name}
        />
        <TextField
          name="email"
          label="Email"
          type="text"
          required
          maxLength={320}
          defaultValue={learner.email}
        />
        <TextField
          name="department"
          label="Department"
          maxLength={120}
          defaultValue={learner.department ?? ""}
        />
        <TextField
          name="business_unit"
          label="Business Unit"
          maxLength={120}
          defaultValue={learner.business_unit ?? ""}
        />
      </div>

      <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800">
        <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">Identity Link</h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
          Link this learner to an identity user account. The user will be able to sign in and
          access their assigned training.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField
            name="user_id"
            label="User ID (UUID)"
            type="text"
            placeholder="00000000-0000-4000-8000-000000000000"
            defaultValue={learner.user_id ?? ""}
          />
        </div>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
          Leave blank to unlink. The user must exist in the system.
        </p>
      </div>
    </AuthoringForm>
  );
}