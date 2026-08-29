"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Image from "next/image";

type InputPayload = {
  productDescription: string;
  productImage: File | null;
};

const acceptedImageTypes = ["image/png", "image/jpeg", "image/webp"];

export default function Home() {
  const [productDescription, setProductDescription] = useState("");
  const [productImage, setProductImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isPrepared, setIsPrepared] = useState(false);
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

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
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
            }}
            placeholder="Example: A wearable device that continuously monitors heart rate and sends alerts to a smartphone."
            rows={9}
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
                  <button type="button" className="secondary-button" onClick={removeImage}>
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
          {isPrepared ? (
            <p className="success-message">
              Input validated. Product details are ready for the next pipeline stage.
            </p>
          ) : null}

          <button className="primary-button" type="submit">
            Analyze Product
          </button>
        </form>
      </section>
    </main>
  );
}
