import { apiFetch } from './apiClient';
import { Brand, OfficialEvaluationResult } from '../types/brand';

export async function fetchBrands(): Promise<Brand[]> {
  return apiFetch<Brand[]>('/api/v1/brands');
}

export async function seedNovaPayBrand(): Promise<Brand> {
  return apiFetch<Brand>('/api/v1/brands/seed/novapay', {
    method: 'POST',
  });
}

export async function createBrand(brandData: Partial<Brand>): Promise<Brand> {
  return apiFetch<Brand>('/api/v1/brands', {
    method: 'POST',
    body: JSON.stringify(brandData),
  });
}

export async function uploadBrandLogo(brandId: string, file: File): Promise<Brand> {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch<Brand>(`/api/v1/brands/${brandId}/logo`, {
    method: 'POST',
    body: formData,
  });
}

export async function evaluateAssetSafety(
  brandId: string,
  candidatePayload: Record<string, unknown>
): Promise<OfficialEvaluationResult> {
  return apiFetch<OfficialEvaluationResult>(`/api/v1/brands/${brandId}/evaluate-asset`, {
    method: 'POST',
    body: JSON.stringify(candidatePayload),
  });
}
