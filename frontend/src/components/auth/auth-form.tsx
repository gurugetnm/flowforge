"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { ApiError } from "@/lib/api";
import { fieldErrors, loginSchema, registerSchema } from "@/lib/validation";

type Mode = "login" | "register";

const COPY = {
  login: {
    title: "Sign in",
    submit: "Sign in",
    switchText: "Need an account?",
    switchLabel: "Create one",
    switchHref: "/register" as const,
  },
  register: {
    title: "Create an account",
    submit: "Create account",
    switchText: "Already have an account?",
    switchLabel: "Sign in",
    switchHref: "/login" as const,
  },
};

export function AuthForm({ mode }: { mode: Mode }) {
  const { signIn, signUp } = useSession();
  const router = useRouter();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const copy = COPY[mode];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const data = Object.fromEntries(new FormData(event.currentTarget));
    const parsed = (mode === "login" ? loginSchema : registerSchema).safeParse(data);

    if (!parsed.success) {
      setErrors(fieldErrors(parsed.error));
      return;
    }

    setErrors({});
    setSubmitting(true);
    try {
      if (mode === "login") {
        await signIn(parsed.data as { email: string; password: string });
      } else {
        await signUp(parsed.data as { email: string; password: string; name: string });
      }
      router.replace("/dashboard");
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "Could not reach the server. Try again.",
      );
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(
          Object.fromEntries(
            Object.entries(error.fieldErrors).map(([key, messages]) => [key, messages[0]]),
          ),
        );
      }
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1 className="text-text text-base font-semibold">{copy.title}</h1>

      <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
        {mode === "register" && (
          <Field label="Name" error={errors.name} required>
            <Input name="name" autoComplete="name" placeholder="Ada Lovelace" />
          </Field>
        )}

        <Field label="Email" error={errors.email} required>
          <Input name="email" type="email" autoComplete="email" placeholder="you@example.com" />
        </Field>

        <Field
          label="Password"
          error={errors.password}
          hint={mode === "register" ? "At least 10 characters." : undefined}
          required
        >
          <Input
            name="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </Field>

        {formError && (
          <p role="alert" className="bg-danger-soft text-danger rounded-md px-3 py-2 text-sm">
            {formError}
          </p>
        )}

        <Button
          type="submit"
          variant="primary"
          loading={submitting}
          className="w-full justify-center"
        >
          {copy.submit}
        </Button>
      </form>

      <p className="text-text-muted mt-4 text-center text-sm">
        {copy.switchText}{" "}
        <Link href={copy.switchHref} className="text-accent font-medium hover:underline">
          {copy.switchLabel}
        </Link>
      </p>
    </>
  );
}
