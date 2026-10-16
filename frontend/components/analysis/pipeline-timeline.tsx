"use client";

import { Check, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

const STEPS: { key: string; label: string; startedOn: string; doneOn: string }[] = [
  {
    key: "features",
    label: "Feature extraction",
    startedOn: "FEATURE_EXTRACTION_STARTED",
    doneOn: "FEATURE_EXTRACTION_COMPLETED",
  },
  {
    key: "search",
    label: "Patent search",
    startedOn: "PATENT_SEARCH_STARTED",
    doneOn: "PATENT_SEARCH_COMPLETED",
  },
  {
    key: "prosecutor",
    label: "Prosecutor",
    startedOn: "PROSECUTOR_STARTED",
    doneOn: "PROSECUTOR_COMPLETED",
  },
  {
    key: "defender",
    label: "Defender",
    startedOn: "DEFENDER_STARTED",
    doneOn: "DEFENDER_COMPLETED",
  },
  {
    key: "design",
    label: "Design engineer",
    startedOn: "DESIGN_ENGINEER_STARTED",
    doneOn: "DESIGN_OPTIONS_GENERATED",
  },
  {
    key: "risk",
    label: "Risk matrix",
    startedOn: "DESIGN_OPTIONS_GENERATED",
    doneOn: "RISK_MATRIX_READY",
  },
  {
    key: "report",
    label: "Final report",
    startedOn: "RISK_MATRIX_READY",
    doneOn: "FINAL_REPORT_READY",
  },
  {
    key: "images",
    label: "Redesign concepts",
    startedOn: "IMAGE_GENERATION_STARTED",
    doneOn: "PIPELINE_COMPLETED",
  },
];

export function PipelineTimeline({ seen }: { seen: Set<string> }) {
  return (
    <ol className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
      {STEPS.map((step) => {
        const done = seen.has(step.doneOn);
        const running = !done && seen.has(step.startedOn);
        return (
          <li key={step.key} className="flex items-center gap-2">
            {done ? (
              <Check className="h-4 w-4 text-success" />
            ) : running ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            ) : (
              <Circle className="h-4 w-4 text-muted-foreground/40" />
            )}
            <span
              className={cn(
                done && "text-foreground",
                running && "font-medium text-foreground",
                !done && !running && "text-muted-foreground",
              )}
            >
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
