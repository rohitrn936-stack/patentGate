"use client";

import { Gavel } from "lucide-react";

import { DisclaimerBanner } from "@/components/analysis/disclaimer-banner";
import type { FinalReport } from "@/lib/types";

function List({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="mb-1 text-sm font-semibold">{title}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function FinalReportView({ report }: { report: FinalReport | null }) {
  if (!report) {
    return <p className="text-sm text-muted-foreground">Consolidating the report…</p>;
  }
  return (
    <div className="space-y-5">
      {report.executive_summary && (
        <p className="text-sm leading-relaxed">{report.executive_summary}</p>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <List title="Key risks" items={report.key_risks} />
        <List title="Important uncertainties" items={report.important_uncertainties} />
        <List title="Recommended next steps" items={report.recommended_next_steps} />
      </div>

      {report.attorney_questions?.length > 0 && (
        <div className="rounded-lg border bg-muted/30 p-4">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Gavel className="h-4 w-4 text-primary" />
            Questions for your patent attorney
          </p>
          <ol className="list-decimal space-y-1.5 pl-5 text-sm">
            {report.attorney_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        </div>
      )}

      <DisclaimerBanner text={report.legal_disclaimer} />
    </div>
  );
}
