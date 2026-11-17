import { useEffect, useState } from "react";
import { api } from "./api";

// The navbar fetches this on every page, so share one request for a short while
let cached = null; // { at, promise }
const TTL_MS = 30000;

export function fetchBilling({ fresh = false } = {}) {
  if (fresh || !cached || Date.now() - cached.at > TTL_MS) {
    const promise = api.get("/api/billing");
    cached = { at: Date.now(), promise };
    promise.catch(() => { cached = null; });
  }
  return cached.promise;
}

export function useBilling({ fresh = false } = {}) {
  const [billing, setBilling] = useState(null);
  useEffect(() => {
    let alive = true;
    fetchBilling({ fresh }).then((b) => alive && setBilling(b)).catch(() => {});
    return () => { alive = false; };
  }, [fresh]);
  return billing;
}
