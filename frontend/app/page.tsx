"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ImagePlus, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { analyses, products } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

const ACCEPTED = ["image/png", "image/jpeg", "image/webp"];
const MAX_IMAGE_BYTES = 700 * 1024; // keep the JSON body small

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function IntakePage() {
  const { user, loading } = useRequireAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [description, setDescription] = useState("");
  const [image, setImage] = useState<{ name: string; dataUrl: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onPickImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) {
      toast.error("Use a PNG, JPEG or WebP image.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      toast.error("Image is over 700 KB - please use a smaller one.");
      return;
    }
    setImage({ name: file.name, dataUrl: await fileToDataUrl(file) });
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const desc = description.trim();
    if (desc.length < 20) {
      toast.error("Add a few sentences describing what the product does.");
      return;
    }
    setSubmitting(true);
    try {
      const name = desc.split(/[.\n]/)[0].slice(0, 80).trim() || "Untitled product";
      const product = await products.create({
        name,
        description: desc,
        image_url: image?.dataUrl ?? null,
      });
      const analysis = await analyses.create(product.id);
      router.push(`/analysis/${analysis.id}`);
    } catch (err: any) {
      toast.error(err?.message || "Could not start the analysis");
      setSubmitting(false);
    }
  }

  if (loading || !user) {
    return (
      <AppShell>
        <div className="mx-auto max-w-2xl space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-48 w-full" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-primary">
            Product intake
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">What does your product do?</h1>
          <p className="text-sm text-muted-foreground">
            Describe the core behaviour, components and workflows. Add an image if
            shape or layout matters. The pipeline extracts features, searches prior
            art, runs a prosecutor/defender debate, proposes design-arounds and
            builds a risk report - streamed live.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Describe the product</CardTitle>
            <CardDescription>
              Facts only - avoid marketing language. The more technical detail, the
              better the analysis.
            </CardDescription>
          </CardHeader>
          <form onSubmit={onSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="description">Product description</Label>
                <Textarea
                  id="description"
                  rows={9}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Example: A water bottle whose cap contains a temperature sensor that measures the liquid and streams readings to a smartphone over Bluetooth Low Energy."
                  disabled={submitting}
                />
              </div>

              <div className="space-y-2">
                <Label>Product image (optional)</Label>
                {image ? (
                  <div className="flex items-center gap-3 rounded-md border p-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={image.dataUrl}
                      alt="Product preview"
                      className="h-16 w-16 rounded object-cover"
                    />
                    <span className="flex-1 truncate text-sm text-muted-foreground">
                      {image.name}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setImage(null)}
                      disabled={submitting}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    disabled={submitting}
                    className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed py-6 text-sm text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                  >
                    <ImagePlus className="h-4 w-4" />
                    Add image (PNG / JPEG / WebP, under 700 KB)
                  </button>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept={ACCEPTED.join(",")}
                  className="hidden"
                  onChange={onPickImage}
                />
              </div>

              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {submitting ? "Starting analysis..." : "Analyze product"}
              </Button>
            </CardContent>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
