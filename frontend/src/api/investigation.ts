/**
 * Investigation domain API — locations, evidence, cases, streaming.
 * @module api/investigation
 */

import { z } from 'zod';
import type { InvestigateRequest, InvestigateResponse } from '../types/investigation';
import {
  InvestigateResponseSchema,
  EvidenceDetailsSchema,
  LocationResponseSchema,
  LocationInfoSchema,
  ChangeLocationResponseSchema,
  CaseListResponseSchema,
  ResetResponseSchema,
} from './schemas';
import { API_BASE_URL, apiCall, streamSSE } from './base';
import type { StreamCallbacks } from './base';
import type {
  EvidenceDetails,
  LocationResponse,
  LocationInfo,
  ChangeLocationResponse,
  CaseListResponse,
} from '../types/investigation';

export async function investigate(
  request: InvestigateRequest,
): Promise<InvestigateResponse> {
  return apiCall('POST', '/api/investigate', InvestigateResponseSchema, request);
}

export async function investigateStream(
  request: InvestigateRequest,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  await streamSSE(
    `${API_BASE_URL}/api/investigate/stream`,
    request,
    callbacks,
    signal,
  );
}

export async function getEvidenceDetails(
  evidenceId: string,
  caseId = 'case_001',
  slot = 'autosave',
): Promise<EvidenceDetails> {
  const path =
    `/api/evidence/${encodeURIComponent(evidenceId)}` +
    `?case_id=${encodeURIComponent(caseId)}` +
    `&slot=${encodeURIComponent(slot)}`;
  return apiCall('GET', path, EvidenceDetailsSchema);
}

export async function getLocation(
  caseId: string,
  locationId: string,
): Promise<LocationResponse> {
  const path =
    `/api/case/${encodeURIComponent(caseId)}` +
    `/location/${encodeURIComponent(locationId)}`;
  return apiCall('GET', path, LocationResponseSchema);
}

export async function getLocations(
  caseId: string,
  sessionId?: string,
): Promise<LocationInfo[]> {
  let path = `/api/case/${encodeURIComponent(caseId)}/locations`;
  if (sessionId) {
    path += `?session_id=${encodeURIComponent(sessionId)}`;
  }
  return apiCall('GET', path, z.array(LocationInfoSchema));
}

export async function changeLocation(
  caseId: string,
  locationId: string,
  _playerId = 'default',
  sessionId?: string,
  slot = 'autosave',
): Promise<ChangeLocationResponse> {
  const body: Record<string, string> = {
    location_id: locationId,
    slot,
  };
  if (sessionId) {
    body.session_id = sessionId;
  }

  const path = `/api/case/${encodeURIComponent(caseId)}/change-location`;
  return apiCall('POST', path, ChangeLocationResponseSchema, body);
}

export async function getCases(): Promise<CaseListResponse> {
  return apiCall('GET', '/api/cases', CaseListResponseSchema);
}

export interface ResetResponse {
  success: boolean;
  message: string;
}

export async function resetCase(
  caseId: string,
): Promise<ResetResponse> {
  const path = `/api/case/${encodeURIComponent(caseId)}/reset`;
  return apiCall('POST', path, ResetResponseSchema);
}
