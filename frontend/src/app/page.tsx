"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/components/providers/session-provider";
import { SkeletonRows } from "@/components/ui/skeleton";

/** Entry point: send visitors to the dashboard or to sign in. */
export default function HomePage() {
  const { user, isLoading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [isLoading, user, router]);

  return (
    <div className="mx-auto max-w-3xl p-8">
      <SkeletonRows rows={2} />
    </div>
  );
}
