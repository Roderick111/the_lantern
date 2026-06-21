/**
 * Briefing domain API — case briefings, teaching questions.
 * @module api/briefing
 */

import type {
  BriefingContent,
  BriefingQuestionResponse,
  BriefingCompleteResponse,
} from '../types/investigation';
import {
  BriefingContentSchema,
  BriefingQuestionResponseSchema,
  BriefingCompleteResponseSchema,
} from './schemas';
import { apiCall } from './base';

export async function getBriefing(
  caseId: string,
  slot = 'autosave',
): Promise<BriefingContent> {
  const path =
    `/api/briefing/${encodeURIComponent(caseId)}` +
    `?slot=${encodeURIComponent(slot)}`;
  return apiCall('GET', path, BriefingContentSchema);
}

export async function askBriefingQuestion(
  caseId: string,
  question: string,
): Promise<BriefingQuestionResponse> {
  const path = `/api/briefing/${encodeURIComponent(caseId)}/question`;
  return apiCall('POST', path, BriefingQuestionResponseSchema, {
    question,
    slot: 'autosave',
  });
}

export async function markBriefingComplete(
  caseId: string,
  slot = 'autosave',
): Promise<BriefingCompleteResponse> {
  const path =
    `/api/briefing/${encodeURIComponent(caseId)}/complete` +
    `?slot=${encodeURIComponent(slot)}`;
  return apiCall('POST', path, BriefingCompleteResponseSchema);
}