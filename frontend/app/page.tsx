"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";

type InputPayload = {
  productDescription: string;
  productImage: File | null;
};

type Agent1Result = {
  success: boolean;
  result?: any;
  error?: string;
};

const acceptedImageTypes = ["image/png", "image/jpeg", "image/webp"];

export default function Home() {
  const [productDescription, setProductDescription] = useState("");
  const [productImage, setProductImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isPrepared, setIsPrepared] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [agent1Result, setAgent1Result] = useState<Agent1Result | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  const handleImageChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextImage = event.target.files?.[0] ?? null;
    setErrorMessage("");
    setIsPrepared(false);
    setAgent1Result(null);

    if (!nextImage) {
      return;
    }

    if (!acceptedImageTypes.includes(nextImage.type)) {
      setProductImage(null);
      setImagePreview(null);
      setErrorMessage("Please choose a PNG, JPG, JPEG, or WEBP image.");
      event.target.value = "";
      return;
    }

    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }

    setProductImage(nextImage);
    setImagePreview(URL.createObjectURL(nextImage));
  };

  const removeImage = () => {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }

    setProductImage(null);
    setImagePreview(null);
    setIsPrepared(false);
    setAgent1Result(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedDescription = productDescription.trim();
    if (!trimmedDescription) {
      setErrorMessage("Describe what your product does before analysis.");
      setIsPrepared(false);
      return;
    }

    const payload: InputPayload = {
      productDescription: trimmedDescription,
      productImage,
    };

    setProductDescription(payload.productDescription);
    setErrorMessage("");
    setIsPrepared(true);
    setIsLoading(true);
    setAgent1Result(null);

    try {
      const response = await fetch("/api/agent1", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ input: payload.productDescription }),
      });

      const data: Agent1Result = await response.json();
      setAgent1Result(data);
    } catch (error) {
      console.error("Agent 1 API error:", error);
      setAgent1Result({
        success: false,
        error: "Failed to connect to backend. Is the server running?",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderResult = () => {
    if (!agent1Result) return null;

    if (agent1Result.success && agent1Result.result) {
      const result = agent1Result.result;
      return (
        <section className="result-stage" aria-labelledby="result-title">
          <h2 id="result-title" className="result-title">
            Analysis Complete
          </h2>
          <div className="result-content">
            <div className="result-section">
              <h3>Product</h3>
              <p><strong>Name:</strong> {result.product?.name || "N/A"}</p>
              <p><strong>Summary:</strong> {result.product?.summary || "N/A"}</p>
            </div>

            <div className="result-section">
              <h3>Components ({result.components?.length || 0})</h3>
              <ul>
                {result.components?.map((c: any) => (
                  <li key={c.id}>
                    <strong>{c.name}</strong> ({c.id}): {c.description}
                    {c.function && <em> — {c.function}</em>}
                  </li>
                ))}
              </ul>
            </div>

            <div className="result-section">
              <h3>Features ({result.features?.length || 0})</h3>
              <ul>
                {result.features?.map((f: any) => (
                  <li key={f.id}>
                    <strong>{f.name}</strong> ({f.id})
                    <br />
                    Component: {f.component} | Function: {f.function}
                    <br />
                    Evidence: {f.evidence} <em>({f.evidence_source})</em>
                    <br />
                    Confidence: {(f.confidence * 100).toFixed(0)}%
                  </li>
                ))}
              </ul>
            </div>

            <div className="result-section">
              <h3>Knowledge Analysis</h3>
              {result.analysis && (
                <>
                  <p><strong>Invention:</strong> {result.analysis.invention}</p>
                  <p><strong>Similarity Score:</strong> {(result.analysis.similarity_score * 100).toFixed(0)}%</p>
                  <p><strong>Explanation:</strong> {result.analysis.similarity_explanation}</p>
                  <p><strong>Disclaimer:</strong> <em>{result.analysis.disclaimer}</em></p>
                  <div>
                    <h4>Similar Known Concepts ({result.analysis.similar_known_concepts?.length || 0})</h4>
                    <ul>
                      {result.analysis.similar_known_concepts?.map((c: any, i: number) => (
                        <li key={i}>
                          <strong>{c.name}</strong> (Score: {(c.similarity_score * 100).toFixed(0)}%)
                          <br />
                          Why similar: {c.why_similar}
                          <br />
                          Matching features: {c.matching_features?.join(", ") || "N/A"}
                          <br />
                          Differences: {c.differences}
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      );
    }

    if (!agent1Result.success) {
      return (
        <section className="result-stage error" aria-labelledby="error-title">
          <h2 id="error-title" className="result-title">Analysis Failed</h2>
          <div className="error-message">
            {agent1Result.error || "Unknown error occurred"}
          </div>
        </section>
      );
    }

    return null;
  };

  return (
    <main className="page-shell">
      <section className="input-stage" aria-labelledby="product-input-title">
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true">
            PG
          </div>
          <div>
            <p className="brand-name">PatentGate</p>
            <p className="brand-tagline">Patent risk research starts here</p>
          </div>
        </div>

        <div className="intro-copy">
          <p className="eyebrow">Product intake</p>
          <h1 id="product-input-title">What does your product do?</h1>
          <p>
            Describe the core behavior, components, and user-facing function.
            Add an image if visual context would help explain the product.
          </p>
        </div>

        <form className="product-form" onSubmit={handleSubmit} noValidate>
          <label className="field-label" htmlFor="product-description">
            Product description
          </label>
          <textarea
            id="product-description"
            className="description-input"
            value={productDescription}
            onChange={(event) => {
              setProductDescription(event.target.value);
              setErrorMessage("");
              setIsPrepared(false);
              setAgent1Result(null);
            }}
            placeholder="Example: A wearable device that continuously monitors heart rate and sends alerts to a smartphone."
            rows={9}
            disabled={isLoading}
          />

          <div className="upload-panel">
            <div>
              <label className="field-label" htmlFor="product-image">
                Product image <span>optional</span>
              </label>
              <p className="upload-hint">PNG, JPG, JPEG, or WEBP. Kept local for now.</p>
            </div>

            <input
              ref={fileInputRef}
              id="product-image"
              className="file-input"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleImageChange}
              disabled={isLoading}
            />

            {imagePreview ? (
              <div className="image-preview-card">
                <Image
                  src={imagePreview}
                  alt="Selected product preview"
                  width={168}
                  height={126}
                  unoptimized
                />
                <div className="image-meta">
                  <p>{productImage?.name}</p>
                  <button type="button" className="secondary-button" onClick={removeImage} disabled={isLoading}>
                    Remove image
                  </button>
                </div>
              </div>
            ) : (
              <label className="upload-dropzone" htmlFor="product-image">
                <span>Add product image</span>
                <small>Use this only if shape, layout, or components matter.</small>
              </label>
            )}
          </div>

          {errorMessage ? <p className="validation-message">{errorMessage}</p> : null}
          {isPrepared && !isLoading && !agent1Result ? (
            <p className="success-message">
              Input validated. Product details are ready for analysis.
            </p>
          ) : null}

          <button className="primary-button" type="submit" disabled={isLoading || !productDescription.trim()}>
            {isLoading ? "Analyzing..." : "Analyze Product"}
          </button>
        </form>
      </section>

      {renderResult()}
    </main>
  );
}