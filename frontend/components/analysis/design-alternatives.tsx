"use client";

import { ImageOff, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { riskVariant } from "@/components/analysis/primitives";
import { mediaUrl } from "@/lib/api";
import type { DesignAlternative, RedesignImage } from "@/lib/types";

export function DesignAlternatives({
  alternatives,
  images,
  imageStatus,
}: {
  alternatives: DesignAlternative[];
  images: Record<number, RedesignImage>;
  imageStatus: "idle" | "running" | "skipped" | "done";
}) {
  if (alternatives.length === 0) {
    return <p className="text-sm text-muted-foreground">Generating design-around options…</p>;
  }
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {alternatives.map((alt) => {
        const img = images[alt.id];
        const url = mediaUrl(img?.image_url);
        return (
          <div key={alt.id} className="flex flex-col rounded-lg border">
            <div className="grid aspect-video place-items-center overflow-hidden rounded-t-lg border-b bg-muted/40">
              {url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={url} alt={`Redesign ${alt.id}`} className="h-full w-full object-cover" />
              ) : imageStatus === "running" ? (
                <span className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> rendering concept…
                </span>
              ) : (
                <span className="flex items-center gap-2 text-xs text-muted-foreground">
                  <ImageOff className="h-4 w-4" />
                  {imageStatus === "skipped" ? "image step skipped" : "no image"}
                </span>
              )}
            </div>
            <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold">Alternative {alt.id}</p>
                <Badge variant={riskVariant(estimatedRisk(alt))} className="capitalize">
                  {estimatedRisk(alt)} risk-reduction
                </Badge>
              </div>
              <p className="text-muted-foreground">{alt.description}</p>
              {alt.avoids_claim_element && (
                <p>
                  <span className="text-muted-foreground">Avoids:</span> {alt.avoids_claim_element}
                </p>
              )}
              {alt.changes_from_original?.length > 0 && (
                <ul className="list-disc pl-4 text-muted-foreground">
                  {alt.changes_from_original.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              )}
              {alt.tradeoff && (
                <p>
                  <span className="text-muted-foreground">Tradeoff:</span> {alt.tradeoff}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function estimatedRisk(alt: DesignAlternative): string {
  const raw = (alt as any).estimated_risk_reduction || (alt as any).risk_reduction || "";
  if (/high/i.test(raw)) return "high";
  if (/low/i.test(raw)) return "low";
  return "medium";
}
