import type { Language } from "../domain/types";

const en = {
  start_placeholder:
    "The Lantern is in public beta. The investigation opens in the next update. Try /help.",
  help:
    "Commands:\n/start — resume or begin\n/casebook — dossier summary\n/language — EN/RU\n/reset — restart case\n/support — help contact\n/terms — terms\n\n" +
    "Send freeform text to investigate. Enter a witness to ask questions. Rites require an explicit spoken formula; questions do not cast them.",
  queued: "Queued — processing your previous action first.",
  engine_unknown:
    "Progress may already be saved. Check your casebook and resend only if needed.",
  delivery_retry: "Re-sending previous result…",
  sessions_disabled: "New sessions are temporarily closed. Try again later.",
  unsupported_media: "Text only for now — send actions and questions as messages.",
  choose_language: "Choose language / Выберите язык:",
  language_set: "Language set to English.",
  cover_prompt: "Tap below when ready to begin the investigation.",
  begin_investigation: "Begin Investigation",
  investigation_started:
    "You enter the case. Describe what you do or examine. Use the buttons for casebook, witnesses, move, and verdict.",
  resumed:
    "Welcome back. Continue investigating in freeform text, or use the buttons below.",
  casebook_title: "Case file",
  casebook_empty: "No progress yet. Begin the investigation first.",
  location_line: "Location: {name}",
  evidence_line: "Evidence ({n}): {list}",
  evidence_none: "none yet",
  turns_line: "LLM turns today: {used}/{limit} (UTC)",
  witnesses_prompt: "Choose a witness to interview:",
  witness_header: "Interview: {name}\nAsk your questions in freeform text.",
  end_interview: "End Interview",
  change_witness: "Change Witness",
  present_evidence: "Present Evidence",
  move_prompt: "Where do you want to go?",
  moved_to: "{name}\n\n{description}",
  already_there: "You are already here: {name}",
  present_prompt: "Present which evidence to {name}?",
  present_none: "No discovered evidence to present yet.",
  evidence_found: "Evidence discovered: {list}",
  cap_reached:
    "Daily investigation limit reached (40 LLM turns). Resets at 00:00 UTC. Navigation and casebook still work.",
  reset_confirm: "Reset case progress? This cannot be undone. Identity is kept.",
  reset_done: "Case reset. Choose Begin Investigation when ready.",
  reset_cancelled: "Reset cancelled.",
  confirm_yes: "Confirm reset",
  confirm_no: "Cancel",
  verdict_suspect: "Accuse which suspect?",
  verdict_evidence: "Cite evidence (toggle), then confirm. Or cancel.",
  verdict_confirm: "Confirm verdict",
  verdict_cancel: "Cancel",
  verdict_need_reasoning: "Send your reasoning as the next message (why this suspect).",
  verdict_result_correct: "Correct. Case solved.",
  verdict_result_wrong: "Incorrect. Attempts remaining: {n}",
  btn_casebook: "Case file",
  btn_witnesses: "Witnesses",
  btn_move: "Travel",
  btn_verdict: "Accuse",
  btn_present: "Show Evidence",
  btn_end_interview: "End Interview",
  btn_change_witness: "Change Witness",
  btn_begin: "Begin Investigation",
  btn_retry: "Retry",
  interview_ended: "Interview ended. Back to investigation.",
  support:
    "Support: message the beta operators on the project channel (or email the site contact). " +
    "Include platform + approx time. Never send tokens, passwords, or case solutions.",
  terms:
    "The Lantern public beta. Solo private DMs only. Narration uses AI (LLM); daily 40-turn cap (UTC). " +
    "We store Telegram id, language, case progress, and job metadata; no public feed. " +
    "Availability not guaranteed. Do not share spoilers. Reset keeps identity.",
  feature_disabled: "This action is temporarily disabled.",
  engine_error: "Something went wrong with the game engine. Try again.",
  engine_conflict: "Action may already be in progress. Snapshot refreshed — resend only if needed.",
  unknown_callback: "Unknown action.",
  need_begin: "Tap Begin Investigation to enter the case.",
  english: "English",
  russian: "Русский",
} as const;

const ru: Record<keyof typeof en, string> = {
  start_placeholder:
    "«Светоч» работает в открытом бета-тесте. Расследование откроется в следующем обновлении. Попробуйте /help.",
  help:
    "Команды:\n/start — продолжить или начать\n/casebook — материалы дела\n/language — EN/RU\n/reset — сброс дела\n/support — поддержка\n/terms — условия\n\n" +
    "Свободный текст — расследование. Выберите свидетеля для допроса. Обряды требуют явной словесной формулы; обычные вопросы их не вызывают.",
  queued: "В очереди — сначала обрабатывается предыдущее действие.",
  engine_unknown:
    "Прогресс, возможно, уже сохранён. Проверьте материалы дела и повторите только при необходимости.",
  delivery_retry: "Повторная отправка предыдущего результата…",
  sessions_disabled: "Новые сессии временно закрыты. Попробуйте позже.",
  unsupported_media: "Пока только текст — действия и вопросы сообщениями.",
  choose_language: "Choose language / Выберите язык:",
  language_set: "Язык: русский.",
  cover_prompt: "Нажмите ниже, когда будете готовы начать расследование.",
  begin_investigation: "Начать расследование",
  investigation_started:
    "Вы на месте. Напишите, что хотите осмотреть или сделать. Кнопки открывают материалы дела, свидетелей, переход между местами и обвинение.",
  resumed: "С возвращением. Продолжайте текстом или кнопками ниже.",
  casebook_title: "Материалы дела",
  casebook_empty: "Пока нет прогресса. Сначала начните расследование.",
  location_line: "Место: {name}",
  evidence_line: "Улики ({n}): {list}",
  evidence_none: "пока нет",
  turns_line: "Ходов расследования сегодня: {used}/{limit} (UTC)",
  witnesses_prompt: "С кем поговорить?",
  witness_header: "Разговор с {name}\nСпрашивайте свободно.",
  end_interview: "Закончить разговор",
  change_witness: "Выбрать другого",
  present_evidence: "Показать улику",
  move_prompt: "Куда отправиться?",
  moved_to: "{name}\n\n{description}",
  already_there: "Вы уже здесь: {name}",
  present_prompt: "Какую улику предъявить {name}?",
  present_none: "Пока нет обнаруженных улик.",
  evidence_found: "Найдены улики: {list}",
  cap_reached:
    "Дневной лимит расследования (40 ходов LLM). Сброс в 00:00 UTC. Навигация и материалы дела доступны.",
  reset_confirm: "Сбросить прогресс дела? Это нельзя отменить. Аккаунт сохранится.",
  reset_done: "Дело сброшено. Нажмите «Начать расследование».",
  reset_cancelled: "Сброс отменён.",
  confirm_yes: "Подтвердить сброс",
  confirm_no: "Отмена",
  verdict_suspect: "Кого вы обвиняете?",
  verdict_evidence: "Выберите улики для обвинения, затем подтвердите.",
  verdict_confirm: "Подтвердить обвинение",
  verdict_cancel: "Отмена",
  verdict_need_reasoning: "Следующим сообщением отправьте обоснование (почему этот подозреваемый).",
  verdict_result_correct: "Верно. Дело раскрыто.",
  verdict_result_wrong: "Неверно. Осталось попыток: {n}",
  btn_casebook: "Материалы дела",
  btn_witnesses: "Свидетели",
  btn_move: "Отправиться",
  btn_verdict: "Обвинение",
  btn_present: "Показать улику",
  btn_end_interview: "Закончить разговор",
  btn_change_witness: "Выбрать другого",
  btn_begin: "Начать расследование",
  btn_retry: "Повторить",
  interview_ended: "Разговор закончен. Возвращаемся к расследованию.",
  support:
    "Поддержка: напишите операторам беты (канал проекта или контакт на сайте). " +
    "Платформа + примерное время. Не присылайте токены, пароли и решения дела.",
  terms:
    "The Lantern — публичная бета. Только личные ЛС. Наррация через ИИ (LLM); лимит 40 ходов/сутки (UTC). " +
    "Храним Telegram id, язык, прогресс и метаданные заданий; без публичной ленты. " +
    "Доступность не гарантируется. Не спойлерьте. Сброс сохраняет аккаунт.",
  feature_disabled: "Действие временно отключено.",
  engine_error: "Ошибка игрового движка. Попробуйте снова.",
  engine_conflict: "Действие, возможно, уже выполняется. Снимок обновлён — повторите только при необходимости.",
  unknown_callback: "Неизвестное действие.",
  need_begin: "Нажмите «Начать расследование».",
  english: "English",
  russian: "Русский",
};

export type StringKey = keyof typeof en;

export function t(lang: Language, key: StringKey, vars?: Record<string, string | number>): string {
  const raw = lang === "ru" ? ru[key] : en[key];
  if (!vars) return raw;
  return raw.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

export function assertCatalogParity(): void {
  const enKeys = Object.keys(en).sort();
  const ruKeys = Object.keys(ru).sort();
  if (enKeys.join(",") !== ruKeys.join(",")) {
    throw new Error("i18n catalog parity failed");
  }
}
