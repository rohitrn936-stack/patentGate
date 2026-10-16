import { AlertTriangle } from "lucide-react";

export function DisclaimerBanner({ text }: { text?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-foreground">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
      <p>
        {text ||
          "This is an AI-assisted preliminary assessment, not legal advice. Patent scope, claim construction, infringement, validity and freedom-to-operate determinations require review by qualified patent counsel."}
      </p>
    </div>
  );
}
