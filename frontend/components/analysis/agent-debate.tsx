"use client";

import { Scale, Shield } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { StageBadge, riskVariant, type StageState } from "@/components/analysis/primitives";
import type { DefenderOutput, ProsecutorOutput } from "@/lib/types";

function Column({
  icon,
  title,
  subtitle,
  state,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  state: StageState;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between border-b bg-muted/40 px-4 py-2.5">
        <div className="flex items-center gap-2">
          {icon}
          <div>
            <p className="text-sm font-semibold">{title}</p>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        <StageBadge state={state} />
      </div>
      <div className="space-y-3 p-4 text-sm">{children}</div>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <p className="text-muted-foreground">{label}</p>;
}

export function AgentDebate({
  prosecutor,
  prosecutorState,
  defender,
  defenderState,
}: {
  prosecutor: ProsecutorOutput | null;
  prosecutorState: StageState;
  defender: DefenderOutput | null;
  defenderState: StageState;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Column
        icon={<Scale className="h-4 w-4 text-destructive" />}
        title="Prosecutor"
        subtitle="Argues the patents could read on the product"
        state={prosecutorState}
      >
        {!prosecutor ? (
          <Empty label={prosecutorState === "running" ? "Building the case…" : "Waiting for patents…"} />
        ) : (
          <>
            <div>
              <p className="mb-1 font-medium">Claim-element mappings</p>
              {prosecutor.claim_element_mappings.length === 0 ? (
                <Empty label="No mappings identified." />
              ) : (
                <ul className="space-y-2">
                  {prosecutor.claim_element_mappings.map((m, i) => (
                    <li key={i} className="rounded-md bg-muted/50 p-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs text-muted-foreground">
                          {m.patent_id}
                        </span>
                        <Badge variant={riskVariant(m.strength)} className="capitalize">
                          {m.strength || "n/a"}
                        </Badge>
                      </div>
                      <p className="mt-1">
                        <span className="text-muted-foreground">Feature</span>{" "}
                        {m.product_feature} <span className="text-muted-foreground">↦ element</span>{" "}
                        {m.claim_element}
                      </p>
                      {m.explanation && (
                        <p className="mt-1 text-muted-foreground">{m.explanation}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {prosecutor.risk_claims.length > 0 && (
              <div>
                <p className="mb-1 font-medium">Risky claims</p>
                <ul className="space-y-1">
                  {prosecutor.risk_claims.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Badge variant={riskVariant(r.risk_level)} className="mt-0.5 capitalize">
                        {r.risk_level || "n/a"}
                      </Badge>
                      <span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {r.patent_id} · claim {r.claim_id}
                        </span>{" "}
                        — {r.reason}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </Column>

      <Column
        icon={<Shield className="h-4 w-4 text-primary" />}
        title="Defender"
        subtitle="Challenges the prosecutor and finds distinctions"
        state={defenderState}
      >
        {!defender ? (
          <Empty
            label={defenderState === "running" ? "Rebutting…" : "Waiting for the prosecutor…"}
          />
        ) : (
          <>
            {defender.overall_assessment && (
              <p className="rounded-md bg-muted/50 p-2">{defender.overall_assessment}</p>
            )}
            <div>
              <p className="mb-1 font-medium">Distinctions</p>
              {defender.distinctions.length === 0 ? (
                <Empty label="None identified." />
              ) : (
                <ul className="list-disc space-y-1 pl-4">
                  {defender.distinctions.map((d, i) => (
                    <li key={i}>
                      <span className="font-medium">{d.claim_element}:</span> {d.distinction}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {defender.weak_claim_elements.length > 0 && (
              <div>
                <p className="mb-1 font-medium">Weak claim elements</p>
                <ul className="space-y-1">
                  {defender.weak_claim_elements.map((w, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Badge variant={riskVariant(w.risk)} className="mt-0.5 capitalize">
                        {w.risk}
                      </Badge>
                      <span>
                        <span className="font-medium">{w.claim_element}</span> — {w.reasoning}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {defender.prior_art_gaps.length > 0 && (
              <div>
                <p className="mb-1 font-medium">Prior-art gaps</p>
                <ul className="list-disc space-y-1 pl-4">
                  {defender.prior_art_gaps.map((g, i) => (
                    <li key={i}>
                      <span className="font-medium">{g.claim_element}:</span> {g.gap}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </Column>
    </div>
  );
}
