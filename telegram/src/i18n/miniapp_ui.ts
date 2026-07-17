import type { Language } from "../domain/types";

const en = {
  app_title: "The Lantern",
  nav_casebook: "Casebook",
  nav_evidence: "Evidence",
  nav_witnesses: "Witnesses",
  nav_verdict: "Verdict",
  loading: "Loading…",
  offline: "You appear offline. Check connection and retry.",
  session_expired: "Session expired. Close and reopen the Mini App.",
  conflict: "Action may already be in progress. Check chat and retry if needed.",
  cap_reached: "Daily LLM limit reached. Navigation still works.",
  empty_evidence: "No evidence discovered yet. Investigate in chat.",
  empty_visited: "Nowhere yet — move in chat or with Move.",
  empty_witness: "No witness selected.",
  select_witness: "Interview",
  present: "Present in chat",
  selected: "Selected",
  close_hint: "Closing — reply arrives in chat.",
  verdict_title: "Submit verdict",
  verdict_suspect: "Suspect",
  verdict_evidence: "Cite evidence",
  verdict_reasoning: "Reasoning",
  verdict_submit: "Submit",
  verdict_confirm: "Confirm accusation",
  verdict_result: "Result",
  validation_reasoning: "Write your reasoning (required).",
  validation_suspect: "Choose a suspect.",
  turns: "Turns today",
  location: "Location",
  visited: "Visited",
  rites: "Rites — cast in chat",
  rites_hint: "Type the rite in freeform Russian or English. English spell names always work.",
  attempts: "Verdict attempts left",
  solved: "Case solved",
  retry: "Retry",
  error_generic: "Something went wrong.",
  restricted: "Restricted",
} as const;

const ru: Record<keyof typeof en, string> = {
  app_title: "Светоч",
  nav_casebook: "Материалы дела",
  nav_evidence: "Улики",
  nav_witnesses: "Свидетели",
  nav_verdict: "Обвинение",
  loading: "Загрузка…",
  offline: "Нет сети. Проверьте соединение и попробуйте снова.",
  session_expired: "Сессия истекла. Закройте мини-приложение и откройте снова.",
  conflict: "Действие, возможно, уже выполняется. Загляните в чат.",
  cap_reached: "Дневной лимит ходов исчерпан. Навигация и материалы дела доступны.",
  empty_evidence: "Улик пока нет — ищите в чате.",
  empty_visited: "Пока нигде не были — отправляйтесь через чат или кнопкой «Отправиться».",
  empty_witness: "Свидетель не выбран.",
  select_witness: "Поговорить",
  present: "Показать в чате",
  selected: "Выбран",
  close_hint: "Закрываем — ответ придёт в чат.",
  verdict_title: "Обвинение",
  verdict_suspect: "Кого обвиняете",
  verdict_evidence: "На какие улики опираетесь",
  verdict_reasoning: "Обоснование",
  verdict_submit: "Отправить",
  verdict_confirm: "Подтвердить обвинение",
  verdict_result: "Итог",
  validation_reasoning: "Нужно написать обоснование.",
  validation_suspect: "Выберите подозреваемого.",
  turns: "Ходов сегодня",
  location: "Место",
  visited: "Посещённые места",
  rites: "Обряды — в чате",
  rites_hint: "Пишите обряд свободно по-русски или по-английски. Английские имена обрядов срабатывают всегда.",
  attempts: "Попыток обвинения",
  solved: "Дело раскрыто",
  retry: "Ещё раз",
  error_generic: "Что-то пошло не так.",
  restricted: "Обряд ограничен",
};

export type MiniUiKey = keyof typeof en;

export function tm(lang: Language, key: MiniUiKey): string {
  return lang === "ru" ? ru[key] : en[key];
}

export function assertMiniUiParity(): void {
  const a = Object.keys(en).sort().join(",");
  const b = Object.keys(ru).sort().join(",");
  if (a !== b) throw new Error("miniapp ui catalog parity failed");
}
