"use client";

import { useRef, useState } from "react";
import PhotoCheckResult from "@/components/PhotoCheckResult";
import { checkPhoto } from "@/lib/api";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 10 * 1024 * 1024;

// Optional: the farmer adds a field photo, which is compared with the satellite evidence.
export default function PhotoUpload({ assessmentId, initialCheck = null }) {
  const inputRef = useRef(null);
  const [check, setCheck] = useState(initialCheck);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow choosing the same file again
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError("The photo is larger than 10 MB. Please choose a smaller photo.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await checkPhoto(assessmentId, file);
      setCheck(data.photo_check);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-line p-3">
      <div>
        <h3 className="text-sm font-semibold text-ink">Add a photo of the field (optional)</h3>
        <p className="text-xs text-ink-muted">
          A photo taken at the field, ideally soon after the event, is compared with the satellite images. Its location
          and date are read from the photo file.
        </p>
      </div>

      {check && !busy && <PhotoCheckResult check={check} compact />}

      {busy ? (
        <p className="flex min-h-11 items-center gap-2 text-sm text-ink" aria-live="polite">
          <span className="size-3 animate-pulse rounded-full bg-brand" />
          Checking your photo against the satellite evidence…
        </p>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="min-h-11 w-full rounded-lg border border-brand px-4 text-sm font-semibold text-brand hover:bg-brand-soft"
        >
          {check ? "Check a different photo" : "Choose or take a photo"}
        </button>
      )}
      <input ref={inputRef} type="file" accept={ACCEPT} onChange={onFile} className="hidden" aria-label="Field photo" />

      {error && (
        <p role="alert" className="rounded-lg bg-danger-soft p-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
