import { z } from "zod";

export type FieldType = "text" | "select";

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  options?: { label: string; value: string }[];
}

export interface FormSchema {
  fields: FormField[];
}

// Example schema from backend
export const mockSchema: FormSchema = {
  fields: [
    {
      name: "fullName",
      label: "Full Name",
      type: "text",
      required: true,
    },
    {
      name: "email",
      label: "Email",
      type: "text",
      required: true,
    },
    {
      name: "role",
      label: "Role",
      type: "select",
      required: true,
      options: [
        { label: "Developer", value: "developer" },
        { label: "Designer", value: "designer" },
        { label: "Manager", value: "manager" },
      ],
    },
    {
      name: "department",
      label: "Department",
      type: "select",
      required: false,
      options: [
        { label: "Engineering", value: "engineering" },
        { label: "Design", value: "design" },
        { label: "Marketing", value: "marketing" },
      ],
    },
  ],
};

export const generateZodSchema = (formSchema: FormSchema) => {
  const schemaMap: Record<string, z.ZodTypeAny> = {};

  formSchema.fields.forEach((field) => {
    switch (field.type) {
      case "select":
        schemaMap[field.name] = field.required
          ? z
              .string()
              .refine(
                (val) => field.options?.some((opt) => opt.value === val),
                {
                  message: `${field.label} must be a valid option`,
                },
              )
          : z
              .string()
              .optional()
              .refine(
                (val) =>
                  !val || field.options?.some((opt) => opt.value === val),
                {
                  message: `${field.label} must be a valid option`,
                },
              );
        break;

      case "text":
      default:
        schemaMap[field.name] = field.required
          ? z.string().min(1, `${field.label} is required`)
          : z.string().optional();
        break;
    }
  });

  return z.object(schemaMap);
};
