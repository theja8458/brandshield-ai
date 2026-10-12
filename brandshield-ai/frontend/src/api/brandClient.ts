import { API_BASE_URL } from '../config';
import { Brand, OfficialEvaluationResult } from '../types/brand';

export async function fetchBrands(): Promise<Brand[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/brands`);
  if (!res.ok) {
    throw new Error(`Failed to fetch brands (${res.status} ${res.statusText})`);
  }
  return res.json();
}

export async function seedNovaPayBrand(): Promise<Brand> {
  const res = await fetch(`${API_BASE_URL}/api/v1/brands/seed/novapay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to seed NovaPay (${res.status})`);
  }
  return res.json();
}

export async function createBrand(brandData: Partial<Brand>): Promise<Brand> {
  const res = await fetch(`${API_BASE_URL}/api/v1/brands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(brandData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create brand (${res.status})`);
  }
  return res.json();
}

export async function uploadBrandLogo(brandId: string, file: File): Promise<Brand> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/api/v1/brands/${brandId}/logo`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to upload logo (${res.status})`);
  }
  return res.json();
}

export async function evaluateAssetSafety(
  brandId: string,
  candidatePayload: Record<string, unknown>
): Promise<OfficialEvaluationResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/brands/${brandId}/evaluate-asset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(candidatePayload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Evaluation failed (${res.status})`);
  }
  return res.json();
}
