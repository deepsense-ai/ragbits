import { z } from "zod";
import { FormSchemaResponse } from "../../types/api.ts";

export const generateZodSchema = (formSchema: FormSchemaResponse) => {
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
