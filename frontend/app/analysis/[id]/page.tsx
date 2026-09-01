"use client";

import { use, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { AgentDebate } from "@/components/analysis/agent-debate";
import { DesignAlternatives } from "@/components/analysis/design-alternatives";
import { DisclaimerBanner } from "@/components/analysis/disclaimer-banner";
import { FinalReportView } from "@/components/analysis/final-report";
import { PatentList } from "@/components/analysis/patent-list";
import { PipelineTimeline } from "@/components/analysis/pipeline-timeline";
import { RiskMatrixCards } from "@/components/analysis/risk-matrix";
import { Section, type StageState } from "@/components/analysis/primitives";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { analyses, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { useAnalysisStream } from "@/hooks/use-analysis-stream";
import type { AnalysisDetail } from "@/lib/types";

type Mode = "loading" | "stream" | "static" | "error";

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, loading } = useRequireAuth();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("loading");
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (loading || !user) return;
    let cancelled = false;
    (async () => {
      try {
        const d = await analyses.get(id);
        if (cancelled) return;
        setDetail(d);
        const finished = d.status === "completed" && !!d.report;
        setMode(finished ? "static" : "stream");
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof ApiError ? err.message : "Could not load this analysis.");
        setMode("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, loading, user]);

  const stream = useAnalysisStream(id, mode === "stream");

  // Unify streamed state and a rehydrated static result behind one shape.
  const view = useMemo(() => {
    if (mode === "static" && detail) {
      const seen = new Set<string>([
        "FEATURE_EXTRACTION_COMPLETED",
        "PATENT_SEARCH_COMPLETED",
        "PROSECUTOR_COMPLETED",
        "DEFENDER_COMPLETED",
        "DESIGN_OPTIONS_GENERATED",
        "RISK_MATRIX_READY",
        "FINAL_REPORT_READY",
        "PIPELINE_COMPLETED",
      ]);
      const images: Record<number, any> = {};
      (detail.images || []).forEach((im: any) => (images[im.option_id] = im));
      return {
        seen,
        done: true,
        error: detail.status === "failed" ? detail.errors?.[0]?.message ?? "Run failed" : null,
        features: detail.feature_extraction,
        patents: detail.patents ?? [],
        prosecutor: detail.prosecutor,
        defender: detail.defender,
        design: detail.design,
        riskMatrix: detail.risk_matrix,
        report: detail.report,
        images,
        imageStatus: (detail.images?.length ? "done" : "skipped") as StageState,
        warnings: [] as string[],
      };
    }
    return {
      seen: stream.seen,
      done: stream.done,
      error: stream.error,
      features: stream.features,
      patents: stream.patents,
      prosecutor: stream.prosecutor,
      defender: stream.defender,
      design: stream.design,
      riskMatrix: stream.riskMatrix,
      report: stream.report,
      images: stream.images,
      imageStatus: stream.imageStatus as StageState,
      warnings: stream.warnings,
    };
  }, [mode, detail, stream]);

  const st = (doneKey: string, startKey?: string): StageState => {
    if (view.seen.has(doneKey)) return "done";
    if (startKey && view.seen.has(startKey)) return "running";
    return "idle";
  };

  if (loading || !user || mode === "loading") {
    return (
      <AppShell>
        <div className="space-y-4">
          <Skeleton className="h-8 w-72" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  if (mode === "error") {
    return (
      <AppShell>
        <div className="mx-auto max-w-md space-y-4 py-12 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">{loadError}</p>
          <Button variant="outline" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" /> New analysis
          </Button>
        </div>
      </AppShell>
    );
  }

  const productSummary =
    view.features?.product?.summary || view.report?.product_summary || "";

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {view.features?.product?.name || "Patent-risk analysis"}
            </h1>
            {productSummary && (
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{productSummary}</p>
            )}
          </div>
          {!view.done && (
            <span className="flex items-center gap-2 whitespace-nowrap text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> streaming
            </span>
          )}
        </div>

        <DisclaimerBanner />

        <div className="rounded-lg border p-4">
          <PipelineTimeline seen={view.seen} />
        </div>

        {view.error && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <span>{view.error}</span>
          </div>
        )}

        {view.warnings.length > 0 && (
          <ul className="rounded-md border border-warning/40 bg-warning/10 p-3 text-xs text-muted-foreground">
            {view.warnings.map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        )}

        <Section
          title="Extracted features"
          state={st("FEATURE_EXTRACTION_COMPLETED", "FEATURE_EXTRACTION_STARTED")}
          count={view.features?.features?.length}
        >
          <div className="flex flex-wrap gap-2">
            {(view.features?.features ?? []).map((f: any) => (
              <span
                key={f.id}
                className="rounded-md border bg-muted/40 px-2 py-1 text-xs"
                title={f.description}
              >
                {f.name}
              </span>
            ))}
          </div>
        </Section>

        <Section
          title="Prior-art patents"
          state={st("PATENT_SEARCH_COMPLETED", "PATENT_SEARCH_STARTED")}
          count={view.patents.length}
        >
          <PatentList patents={view.patents} />
        </Section>

        <Section
          title="Prosecutor vs Defender"
          state={
            st("DEFENDER_COMPLETED", "PROSECUTOR_STARTED") === "done"
              ? "done"
              : view.seen.has("PROSECUTOR_STARTED")
                ? "running"
                : "idle"
          }
        >
          <AgentDebate
            prosecutor={view.prosecutor}
            prosecutorState={st("PROSECUTOR_COMPLETED", "PROSECUTOR_STARTED")}
            defender={view.defender}
            defenderState={st("DEFENDER_COMPLETED", "DEFENDER_STARTED")}
          />
        </Section>

        <Section
          title="Patent risk matrix"
          state={st("RISK_MATRIX_READY", "DESIGN_OPTIONS_GENERATED")}
        >
          <RiskMatrixCards matrix={view.riskMatrix} />
        </Section>

        <Section
          title="Design-around alternatives"
          state={st("DESIGN_OPTIONS_GENERATED", "DESIGN_ENGINEER_STARTED")}
          count={view.design?.alternatives?.length}
        >
          <DesignAlternatives
            alternatives={view.design?.alternatives ?? []}
            images={view.images}
            imageStatus={
              (["idle", "running", "skipped", "done"].includes(view.imageStatus as string)
                ? view.imageStatus
                : "idle") as any
            }
          />
        </Section>

        <Section
          title="Consolidated report"
          state={st("FINAL_REPORT_READY", "RISK_MATRIX_READY")}
        >
          <FinalReportView report={view.report} />
        </Section>
      </div>
    </AppShell>
  );
}
