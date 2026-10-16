"use client";

import { Badge } from "@/components/ui/badge";
import { riskVariant } from "@/components/analysis/primitives";
import type { RiskMatrix } from "@/lib/types";

export function RiskMatrixCards({ matrix }: { matrix: RiskMatrix | null }) {
  if (!matrix) {
    return <p className="text-sm text-muted-foreground">Scoring claim elements…</p>;
  }
  const dot = (lvl?: string | null) =>
    ({ HIGH: "bg-destructive", MEDIUM: "bg-warning", LOW: "bg-success" } as Record<string, string>)[
      (lvl || "").toUpperCase()
    ] || "bg-muted-foreground";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-md border p-3 text-sm">
        <span className="font-medium">Overall exposure</span>
        <Badge variant={riskVariant(matrix.overall_risk)} className="text-sm">
          {matrix.overall_risk ?? "n/a"}
        </Badge>
        {typeof matrix.overall_score === "number" && (
          <span className="text-muted-foreground">score {matrix.overall_score}/100</span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {matrix.risks.map((r, i) => (
          <div key={i} className="rounded-md border p-3">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium">{r.claim_element}</p>
              <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${dot(r.risk_level)}`} />
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant={riskVariant(r.risk_level)} className="capitalize">
                {r.risk_level}
              </Badge>
              <span>score {r.score}/100</span>
            </div>
            <p className="mt-2 text-sm">{r.reason}</p>
            {r.distinction && (
              <p className="mt-1 text-sm text-muted-foreground">Distinction: {r.distinction}</p>
            )}
            {r.recommended_action && (
              <p className="mt-1 text-sm text-muted-foreground">Next: {r.recommended_action}</p>
            )}
            {r.supporting_patents?.length > 0 && (
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {r.supporting_patents.join(", ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
