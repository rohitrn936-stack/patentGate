"use client";

import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type StageState = "idle" | "running" | "done" | "skipped" | "error";

export function StageBadge({ state }: { state: StageState }) {
  const map: Record<StageState, { label: string; variant: any }> = {
    idle: { label: "Waiting", variant: "outline" },
    running: { label: "Running", variant: "secondary" },
    done: { label: "Done", variant: "success" },
    skipped: { label: "Skipped", variant: "outline" },
    error: { label: "Error", variant: "destructive" },
  };
  const { label, variant } = map[state];
  return (
    <Badge variant={variant} className="gap-1">
      {state === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {label}
    </Badge>
  );
}

export function Section({
  title,
  state,
  count,
  children,
  className,
}: {
  title: string;
  state: StageState;
  count?: number;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("scroll-mt-20", className)}>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {title}
          {typeof count === "number" && count > 0 && (
            <span className="text-xs font-normal text-muted-foreground">({count})</span>
          )}
        </CardTitle>
        <StageBadge state={state} />
      </CardHeader>
      <CardContent>
        {state === "idle" ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}

export function riskVariant(level?: string | null): any {
  switch ((level || "").toUpperCase()) {
    case "HIGH":
      return "destructive";
    case "MEDIUM":
      return "warning";
    case "LOW":
      return "success";
    default:
      return "outline";
  }
}
