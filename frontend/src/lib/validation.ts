import { z } from "zod";

export const MIN_PASSWORD_LENGTH = 10;

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

export const registerSchema = z.object({
  name: z.string().trim().min(1, "Enter your name.").max(120, "That name is too long."),
  email: z.email("Enter a valid email address."),
  password: z
    .string()
    .min(MIN_PASSWORD_LENGTH, `Use at least ${MIN_PASSWORD_LENGTH} characters.`)
    .max(200, "That password is too long."),
});

export const workflowSchema = z.object({
  name: z.string().trim().min(1, "Give the workflow a name.").max(120, "That name is too long."),
  description: z.string().max(2000, "That description is too long.").default(""),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type WorkflowValues = z.infer<typeof workflowSchema>;

/** Flatten a Zod error into the `{ field: message }` shape forms render. */
export function fieldErrors(error: z.ZodError): Record<string, string> {
  const result: Record<string, string> = {};
  for (const issue of error.issues) {
    const key = issue.path.join(".") || "_";
    result[key] ??= issue.message;
  }
  return result;
}
