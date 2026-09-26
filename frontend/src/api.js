let rawBase = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").trim().replace(/\/+$/, "");
const API_BASE = rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`;

export async function fetchAvailableDays() {
  const res = await fetch(`${API_BASE}/days`);
  if (!res.ok) throw new Error("Failed to fetch available clinic days");
  return res.json();
}

export async function fetchEODBundle(date, clinicId = "CLN-KNP-014") {
  const res = await fetch(`${API_BASE}/reports/eod-bundle?date=${date}&clinic_id=${clinicId}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch EOD report for ${date}`);
  }
  return res.json();
}

export async function uploadBillingFile(file, strict = false) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/ingest/file?strict=${strict}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || errorData.detail || "Failed to upload billing log");
  }
  return res.json();
}

export async function ingestJsonPayload(jsonArray, strict = false) {
  const res = await fetch(`${API_BASE}/ingest?strict=${strict}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(jsonArray),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || errorData.detail || "Failed to ingest billing log");
  }
  return res.json();
}

export async function updateVisitRecord(visit) {
  const res = await fetch(`${API_BASE}/visits/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(visit),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update visit record");
  }
  return res.json();
}
