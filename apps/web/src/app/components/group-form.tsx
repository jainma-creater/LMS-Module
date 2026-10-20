"use client";

import { updateGroup } from "@/app/actions";

import { AuthoringForm, SelectField, TextAreaField, TextField } from "./authoring-form";

const GROUP_KINDS = [
  { value: "team", label: "Team" },
  { value: "department", label: "Department" },
  { value: "organization", label: "Organization" },
] as const;

interface Group {
  id: string;
  name: string;
  description: string | null;
  kind: string;
  status: string;
}

export default function GroupForm({ group }: { group: Group }) {
  return (
    <AuthoringForm
      action={updateGroup}
      idPrefix={`group-${group.id}`}
      submitLabel="Save group"
      pendingLabel="Saving…"
    >
      <input type="hidden" name="group_id" value={group.id} />

      <TextField
        name="name"
        label="Name"
        required
        maxLength={120}
        defaultValue={group.name}
      />
      <TextAreaField
        name="description"
        label="Description"
        rows={3}
        maxLength={2000}
        defaultValue={group.description ?? ""}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          name="kind"
          label="Kind"
          options={GROUP_KINDS.map((k) => ({ value: k.value, label: k.label }))}
          defaultValue={group.kind}
        />
        <SelectField
          name="status"
          label="Status"
          options={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
          defaultValue={group.status}
        />
      </div>
    </AuthoringForm>
  );
}