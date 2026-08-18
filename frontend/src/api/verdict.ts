/**
 * Verdict domain API — case resolution.
 * @module api/verdict
 */

import type {
  SubmitVerdictRequest,
  SubmitVerdictResponse,
} from '../types/investigation';
import { SubmitVerdictResponseSchema } from './schemas';
import { apiCall } from './base';

export async function submitVerdict(
  request: SubmitVerdictRequest,
): Promise<SubmitVerdictResponse> {
  return apiCall('POST', '/api/submit-verdict', SubmitVerdictResponseSchema, {
    case_id: request.case_id ?? 'case_001',
    accused_suspect_id: request.accused_suspect_id,
    reasoning: request.reasoning,
    evidence_cited: request.evidence_cited,
    slot: request.slot ?? 'autosave',
  });
}
