"use client";

import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { PatentHit } from "@/lib/types";

export function PatentList({ patents }: { patents: PatentHit[] }) {
  if (patents.length === 0) {
    return <p className="text-sm text-muted-foreground">Searching prior art…</p>;
  }
  return (
    <ul className="space-y-3">
      {patents.map((p, i) => (
        <li key={`${p.patent_number}-${i}`} className="rounded-md border p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="flex flex-wrap items-center gap-2 font-medium">
                <span className="font-mono text-xs text-muted-foreground">
                  {p.patent_number || "—"}
                </span>
                {p.title || "Untitled"}
              </p>
              {(p.assignee || p.publication_date || p.filing_date) && (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {[p.assignee, p.filing_date && `filed ${p.filing_date}`, p.publication_date && `pub ${p.publication_date}`]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge variant="outline" className="capitalize">{p.source || "n/a"}</Badge>
              {p.source_url && (
                <a
                  href={p.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="Open source"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
          {p.abstract && (
            <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{p.abstract}</p>
          )}
          {p.matching_features?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {p.matching_features.slice(0, 6).map((f, j) => (
                <Badge key={j} variant="secondary" className="font-normal">
                  {f}
                </Badge>
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
