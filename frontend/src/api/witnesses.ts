/**
 * Witness domain API — interrogation, evidence presentation, streaming.
 * @module api/witnesses
 */

import { z } from 'zod';
import type {
  InterrogateRequest,
  InterrogateResponse,
  PresentEvidenceRequest,
  PresentEvidenceResponse,
  WitnessInfo,
} from '../types/investigation';
import {
  WitnessInfoSchema,
  InterrogateResponseSchema,
  PresentEvidenceResponseSchema,
} from './schemas';
import { API_BASE_URL, apiCall, streamSSE } from './base';
import type { StreamCallbacks } from './base';

export async function getWitnesses(
  caseId = 'case_001',
  slot = 'autosave',
  language = 'en',
): Promise<WitnessInfo[]> {
  let path =
    `/api/witnesses?case_id=${encodeURIComponent(caseId)}` +
    `&slot=${encodeURIComponent(slot)}`;
  if (language !== 'en') path += `&language=${encodeURIComponent(language)}`;
  return apiCall('GET', path, z.array(WitnessInfoSchema));
}

export async function getWitness(
  witnessId: string,
  caseId = 'case_001',
  slot = 'autosave',
): Promise<WitnessInfo> {
  const path =
    `/api/witness/${encodeURIComponent(witnessId)}` +
    `?case_id=${encodeURIComponent(caseId)}` +
    `&slot=${encodeURIComponent(slot)}`;
  return apiCall('GET', path, WitnessInfoSchema);
}

export async function interrogateWitness(
  request: InterrogateRequest,
): Promise<InterrogateResponse> {
  return apiCall('POST', '/api/interrogate', InterrogateResponseSchema, request);
}

export async function interrogateStream(
  request: InterrogateRequest,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  await streamSSE(
    `${API_BASE_URL}/api/interrogate/stream`,
    request,
    callbacks,
    signal,
  );
}

export async function presentEvidence(
  request: PresentEvidenceRequest,
): Promise<PresentEvidenceResponse> {
  return apiCall('POST', '/api/present-evidence', PresentEvidenceResponseSchema, request);
}

export async function presentEvidenceStream(
  request: PresentEvidenceRequest,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  await streamSSE(
    `${API_BASE_URL}/api/present-evidence/stream`,
    request,
    callbacks,
    signal,
  );
}
