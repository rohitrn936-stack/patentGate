"use client";

import { useEffect, useReducer, useRef } from "react";

import { analyses } from "@/lib/api";
import type {
  DefenderOutput,
  FinalReport,
  PatentHit,
  PipelineEvent,
  ProsecutorOutput,
  RedesignImage,
  RiskMatrix,
} from "@/lib/types";

export type StreamState = {
  connected: boolean;
  done: boolean;
  error: string | null;
  stage: string | null;
  events: PipelineEvent[];
  seen: Set<string>;
  features: any | null;
  patents: PatentHit[];
  patentSearch: {
    queries: string[];
    sources_used: string[];
    warnings: string[];
    count: number;
  } | null;
  prosecutor: ProsecutorOutput | null;
  defender: DefenderOutput | null;
  design: { alternatives: any[]; legal_disclaimer?: string } | null;
  riskMatrix: RiskMatrix | null;
  report: FinalReport | null;
  images: Record<number, RedesignImage>;
  imageStatus: "idle" | "running" | "skipped" | "done";
  warnings: string[];
};

const INITIAL: StreamState = {
  connected: false,
  done: false,
  error: null,
  stage: null,
  events: [],
  seen: new Set(),
  features: null,
  patents: [],
  patentSearch: null,
  prosecutor: null,
  defender: null,
  design: null,
  riskMatrix: null,
  report: null,
  images: {},
  imageStatus: "idle",
  warnings: [],
};

type Action =
  | { kind: "open" }
  | { kind: "event"; event: PipelineEvent }
  | { kind: "fatal"; message: string };

function reducer(state: StreamState, action: Action): StreamState {
  if (action.kind === "open") return { ...state, connected: true, error: null };
  if (action.kind === "fatal") {
    if (state.done) return { ...state, connected: false };
    return { ...state, connected: false, done: true, error: action.message };
  }

  const e = action.event;
  const next: StreamState = {
    ...state,
    connected: true,
    stage: e.stage ?? state.stage,
    events: [...state.events, e],
    seen: new Set(state.seen).add(e.type),
  };

  switch (e.type) {
    case "FEATURE_EXTRACTION_COMPLETED":
      next.features = e.data;
      break;
    case "PATENT_FOUND":
      next.patents = [...state.patents, e.data as PatentHit];
      break;
    case "PATENT_SEARCH_COMPLETED":
      next.patentSearch = e.data;
      break;
    case "PROSECUTOR_COMPLETED":
      next.prosecutor = e.data;
      break;
    case "DEFENDER_COMPLETED":
      next.defender = e.data;
      break;
    case "DESIGN_OPTIONS_GENERATED":
      next.design = e.data;
      break;
    case "RISK_MATRIX_READY":
      next.riskMatrix = e.data;
      break;
    case "FINAL_REPORT_READY":
      next.report = e.data;
      break;
    case "IMAGE_GENERATION_STARTED":
      next.imageStatus = "running";
      break;
    case "IMAGE_GENERATION_SKIPPED":
      next.imageStatus = "skipped";
      if (e.message) next.warnings = [...state.warnings, e.message];
      break;
    case "REDESIGN_IMAGE_READY": {
      const img = e.data as RedesignImage;
      next.images = { ...state.images, [img.option_id]: img };
      break;
    }
    case "WARNING":
      if (e.message) next.warnings = [...state.warnings, e.message];
      break;
    case "PIPELINE_COMPLETED":
      next.done = true;
      next.connected = false;
      if (next.imageStatus === "running") next.imageStatus = "done";
      break;
    case "ERROR":
      next.error = e.message ?? "Pipeline error";
      next.done = true;
      next.connected = false;
      break;
  }
  return next;
}

const EVENT_TYPES = [
  "USER_INPUT",
  "FEATURE_EXTRACTION_STARTED",
  "FEATURE_EXTRACTION_COMPLETED",
  "PATENT_SEARCH_STARTED",
  "PATENT_FOUND",
  "PATENT_SEARCH_COMPLETED",
  "PROSECUTOR_STARTED",
  "PROSECUTOR_COMPLETED",
  "DEFENDER_STARTED",
  "DEFENDER_COMPLETED",
  "DESIGN_ENGINEER_STARTED",
  "DESIGN_OPTIONS_GENERATED",
  "RISK_MATRIX_READY",
  "FINAL_REPORT_READY",
  "IMAGE_GENERATION_STARTED",
  "IMAGE_GENERATION_SKIPPED",
  "REDESIGN_IMAGE_READY",
  "WARNING",
  "PIPELINE_COMPLETED",
  "ERROR",
];

export function useAnalysisStream(id: string, enabled: boolean) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!enabled || startedRef.current) return;
    startedRef.current = true;

    const es = new EventSource(analyses.streamUrl(id));
    es.onopen = () => dispatch({ kind: "open" });

    const handler = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as PipelineEvent;
        dispatch({ kind: "event", event: parsed });
        if (parsed.type === "PIPELINE_COMPLETED" || parsed.type === "ERROR") {
          es.close();
        }
      } catch {
        /* ignore keep-alives */
      }
    };
    EVENT_TYPES.forEach((t) => es.addEventListener(t, handler as EventListener));

    es.onerror = () => {
      // EventSource also fires onerror on a normal server-side close. If the
      // pipeline already reported completion the reducer has set `done`, so a
      // late connection error is harmless; otherwise flag it.
      es.close();
      dispatch({ kind: "fatal", message: "Connection to the analysis stream was lost." });
    };

    return () => es.close();
  }, [id, enabled]);

  return state;
}
