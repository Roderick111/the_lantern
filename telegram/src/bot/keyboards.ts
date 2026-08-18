import type { Language } from "../domain/types";
import type { InlineButton } from "../domain/types";
import {
  encodeBegin,
  encodeEndWitness,
  encodeLang,
  encodeMove,
  encodeNav,
  encodePresentEvidence,
  encodeReset,
  encodeRetry,
  encodeVerdictCancel,
  encodeVerdictConfirm,
  encodeVerdictSuspect,
  encodeVerdictToggleEv,
  encodeWitness,
} from "../domain/callbacks";
import {
  LOCATION_IDS,
  LOCATION_NAMES,
  SUSPECT_IDS,
  WITNESS_IDS,
  WITNESS_NAMES,
  type LocationId,
  type WitnessId,
} from "../domain/case_meta";
import { t } from "../i18n/strings";

export function languageKeyboard(): InlineButton[][] {
  return [
    [
      { text: "English", callback_data: encodeLang("en") },
      { text: "Русский", callback_data: encodeLang("ru") },
    ],
  ];
}

export function beginKeyboard(lang: Language): InlineButton[][] {
  return [[{ text: t(lang, "btn_begin"), callback_data: encodeBegin() }]];
}

/** Deep-link Mini App routes when publicUrl set; else callback fallback. */
export function investigationKeyboard(
  lang: Language,
  publicUrl?: string,
): InlineButton[][] {
  const base = publicUrl?.replace(/\/$/, "");
  const open = (route: string, label: string, cb: string): InlineButton =>
    base
      ? { text: label, web_app: { url: `${base}/app/#/${route}` } }
      : { text: label, callback_data: cb };

  return [
    [
      open("casebook", t(lang, "btn_casebook"), encodeNav("casebook")),
      open("witnesses", t(lang, "btn_witnesses"), encodeNav("witnesses")),
    ],
    [
      { text: t(lang, "btn_move"), callback_data: encodeNav("move") },
      open("verdict", t(lang, "btn_verdict"), encodeNav("verdict")),
    ],
  ];
}

export function witnessKeyboard(
  lang: Language,
  publicUrl?: string,
): InlineButton[][] {
  const base = publicUrl?.replace(/\/$/, "");
  const present: InlineButton = base
    ? {
        text: t(lang, "btn_present"),
        web_app: { url: `${base}/app/#/evidence?present=1` },
      }
    : { text: t(lang, "btn_present"), callback_data: encodeNav("present") };
  const change: InlineButton = base
    ? {
        text: t(lang, "btn_change_witness"),
        web_app: { url: `${base}/app/#/witnesses` },
      }
    : {
        text: t(lang, "btn_change_witness"),
        callback_data: encodeNav("witnesses"),
      };

  return [
    [present, change],
    [{ text: t(lang, "btn_end_interview"), callback_data: encodeEndWitness() }],
  ];
}

export function moveKeyboard(
  lang: Language,
  locations?: Array<{ id: string; name: string }>,
): InlineButton[][] {
  const labels = new Map(locations?.map((location) => [location.id, location.name]));
  const ids =
    locations && locations.length > 0
      ? locations.map((location) => location.id)
      : [...LOCATION_IDS];
  return ids.map((id) => {
    const names = LOCATION_NAMES[id as LocationId];
    const fallback = names
      ? lang === "ru"
        ? names.ru
        : names.en
      : id;
    const label = labels.get(id) ?? fallback;
    return [{ text: label, callback_data: encodeMove(id) }];
  });
}

export function witnessesKeyboard(
  lang: Language,
  witnesses?: Array<{ id: string; name: string }>,
): InlineButton[][] {
  const labels = new Map(witnesses?.map((witness) => [witness.id, witness.name]));
  const ids =
    witnesses && witnesses.length > 0
      ? witnesses.map((witness) => witness.id)
      : [...WITNESS_IDS];
  return ids.map((id) => {
    const names = WITNESS_NAMES[id as WitnessId];
    const fallback = names
      ? lang === "ru"
        ? names.ru
        : names.en
      : id;
    const label = labels.get(id) ?? fallback;
    return [{ text: label, callback_data: encodeWitness(id) }];
  });
}

export function presentEvidenceKeyboard(
  evidenceIds: string[],
  evidenceNames: Record<string, string>,
): InlineButton[][] {
  return evidenceIds.map((id) => [
    {
      text: evidenceNames[id] ?? id,
      callback_data: encodePresentEvidence(id),
    },
  ]);
}

export function resetKeyboard(lang: Language): InlineButton[][] {
  return [
    [
      { text: t(lang, "confirm_yes"), callback_data: encodeReset(true) },
      { text: t(lang, "confirm_no"), callback_data: encodeReset(false) },
    ],
  ];
}

export function verdictSuspectKeyboard(lang: Language): InlineButton[][] {
  return SUSPECT_IDS.map((id) => {
    const names = WITNESS_NAMES[id as WitnessId];
    const label = lang === "ru" ? names.ru : names.en;
    return [{ text: label, callback_data: encodeVerdictSuspect(id) }];
  });
}

export function verdictEvidenceKeyboard(
  evidenceIds: string[],
  evidenceNames: Record<string, string>,
  selected: Set<string>,
  lang: Language,
): InlineButton[][] {
  const rows = evidenceIds.map((id) => {
    const mark = selected.has(id) ? "✓ " : "";
    return [
      {
        text: `${mark}${evidenceNames[id] ?? id}`,
        callback_data: encodeVerdictToggleEv(id),
      },
    ];
  });
  rows.push([
    { text: t(lang, "verdict_confirm"), callback_data: encodeVerdictConfirm() },
    { text: t(lang, "verdict_cancel"), callback_data: encodeVerdictCancel() },
  ]);
  return rows;
}

export function retryKeyboard(lang: Language): InlineButton[][] {
  return [[{ text: t(lang, "btn_retry"), callback_data: encodeRetry() }]];
}

/** grammY InlineKeyboardMarkup shape. */
export function toTelegramMarkup(rows: InlineButton[][] | undefined): {
  inline_keyboard: {
    text: string;
    callback_data?: string;
    web_app?: { url: string };
  }[][];
} | undefined {
  if (!rows || rows.length === 0) return undefined;
  return {
    inline_keyboard: rows.map((row) =>
      row.map((b) => {
        if (b.web_app) return { text: b.text, web_app: b.web_app };
        return { text: b.text, callback_data: b.callback_data ?? "noop" };
      }),
    ),
  };
}
