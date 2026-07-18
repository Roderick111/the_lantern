/** Deprecated offline fallback for tests/engine outages. Live case text comes from the backend locale overlay. */

import type { Language } from "../domain/types";
import {
  LOCATION_IDS,
  LOCATION_NAMES,
  WITNESS_IDS,
  WITNESS_NAMES,
  type LocationId,
  type WitnessId,
} from "../domain/case_meta";

export interface LocalizedText {
  en: string;
  ru: string;
}

export interface EvidenceCatalogEntry {
  name: LocalizedText;
  description: LocalizedText;
  type: string;
  location_id: string;
}

export interface WitnessCatalogEntry {
  name: LocalizedText;
  bio: LocalizedText;
}

export interface RiteCatalogEntry {
  id: string;
  name: LocalizedText;
  help: LocalizedText;
}

export const CASE_META = {
  id: "case_001",
  title: { en: "The Sealed Archive", ru: "Опечатанная библиотека" },
  synopsis: {
    en:
      "Professor Aldric Vane lies frozen in Blackwood's sealed archive. " +
      "Three suspects, two thefts, and a spell no one will claim. The first answer looks obvious. That is why it cannot be trusted.",
    ru:
      "Профессор Аркадий Вежин застыл в опечатанной библиотеке Чернолесской коллегии. " +
      "Трое подозреваемых, две кражи, два следа чар, и ни одного признания. Самый простой ответ слишком хорошо ложится на руку.",
  },
} as const;

/** Discovered-evidence display only, no points_to / solution fields. */
export const EVIDENCE_CATALOG: Record<string, EvidenceCatalogEntry> = {
  hidden_note: {
    name: { en: "Crumpled Apology Note", ru: "Смятая извинительная записка" },
    description: {
      en: "Childlike handwriting. Mentions nightshade and a sick friend. Signed “D.”",
      ru: "Детский почерк. Упоминает белладонну и больного друга. Подпись «D.»",
    },
    type: "documentary",
    location_id: "library",
  },
  focus_signature: {
    name: { en: "Professor Vane's Focus Signature", ru: "Сигнатура фокуса профессора Вежина" },
    description: {
      en: "Last acts: Raise the Lamp, then an attempted Dispel. No offensive cast.",
      ru: "Последние действия: поднять лампу, затем попытаться снять чары. Следов нападения нет.",
    },
    type: "magical",
    location_id: "library",
  },
  frost_pattern: {
    name: { en: "Unusual Frost Pattern", ru: "Необычный узор инея" },
    description: {
      en: "Frost that does not match the weather, concentrated near the ritual space.",
      ru: "Иней не по погоде: он сгущается вокруг места обряда.",
    },
    type: "physical",
    location_id: "library",
  },
  dual_shimmer: {
    name: { en: "Dual-Tone Shimmer on Professor Vane", ru: "Двойной отблеск на профессоре Вежине" },
    description: {
      en: "Two overlapping sheens on the skin, pale blue-white and a faint yellowish-green.",
      ru: "Два наложенных отблеска на коже, бледно-голубой и слабый желто-зелёный.",
    },
    type: "magical",
    location_id: "library",
  },
  dropped_badge: {
    name: { en: "Elena's Library Badge", ru: "Библиотечный жетон Елены" },
    description: {
      en: "Scarlet Court library badge found near the scene.",
      ru: "Библиотечный жетон Алого двора у места происшествия.",
    },
    type: "physical",
    location_id: "library",
  },
  scuff_marks: {
    name: { en: "Scuff Marks on Floor", ru: "Царапины на полу" },
    description: {
      en: "Fresh scuffs leading toward the exit corridor.",
      ru: "Свежие следы в сторону выходного коридора.",
    },
    type: "physical",
    location_id: "library",
  },
  singed_cloak_fiber: {
    name: { en: "Singed Fabric Fiber", ru: "Опалённое волокно ткани" },
    description: {
      en: "Expensive green fabric fiber, heat-damaged.",
      ru: "Дорогое зелёное волокно, повреждённое жаром.",
    },
    type: "physical",
    location_id: "library",
  },
  ritual_book: {
    name: { en: "Open Book on Reading Desk", ru: "Открытая книга на пюпитре" },
    description: {
      en: "Open text on a dark ritual procedure, candle wax nearby.",
      ru: "Открытый текст о тёмном обряде, рядом воск свечи.",
    },
    type: "documentary",
    location_id: "library",
  },
  elena_book_slip: {
    name: { en: "Library Access Slip and Book", ru: "Читательский лист и книга" },
    description: {
      en: "Access slip placing Elena in the sealed archive that evening with a research volume.",
      ru: "Лист, ставящий Елену в стеллажах тем вечером с исследовательской книгой.",
    },
    type: "documentary",
    location_id: "library",
  },
  hawthorne_confiscation_log: {
    name: { en: "Miss Hawthorne's Confiscation Notes", ru: "Заметки мисс Боярышниковой о конфискациях" },
    description: {
      en: "Staff notes on recent confiscations and restricted materials.",
      ru: "Заметки персонала о недавних конфискациях и ограниченных материалах.",
    },
    type: "documentary",
    location_id: "library",
  },
  damaged_ward_stone: {
    name: { en: "Stressed Ward Stone", ru: "Надломленный камень защиты" },
    description: {
      en: "Ward stone under stress, breach residue at the eastern alcove approach.",
      ru: "Камень защиты под нагрузкой, следы взлома у восточной ниши.",
    },
    type: "magical",
    location_id: "library",
  },
  torn_letter: {
    name: { en: "Letter from Lord Magnus Thorne", ru: "Письмо старшего господина Мстислава Тернского" },
    description: {
      en: "Torn correspondence mentioning a Thief's Candle and family expectation.",
      ru: "Оборванное письмо о Свече Вора и долге перед семьёй.",
    },
    type: "documentary",
    location_id: "iron_lodge_common_room",
  },
  stolen_nightshade: {
    name: { en: "Stolen Nightshade", ru: "Украденная белладонна" },
    description: {
      en: "Nightshade stores found where they should not be.",
      ru: "Запасы белладонны найдены не там, где должны быть.",
    },
    type: "physical",
    location_id: "iron_lodge_common_room",
  },
  residual_dark_magic: {
    name: { en: "Dark Magic Residue", ru: "Остаток тёмной магии" },
    description: {
      en: "Residual craft signature in the common room area.",
      ru: "Остаточная сигнатура ремесла в зоне гостиной.",
    },
    type: "magical",
    location_id: "iron_lodge_common_room",
  },
  student_testimony: {
    name: { en: "Iron Lodge Student Accounts", ru: "Показания учеников Железного двора" },
    description: {
      en: "Students describe someone leaving and returning terrified that night.",
      ru: "Студенты описывают, как кто-то ушёл и вернулся в ужасе той ночью.",
    },
    type: "testimonial",
    location_id: "iron_lodge_common_room",
  },
  cassian_unsent_letter: {
    name: { en: "Cassian's Unsent Letter", ru: "Неотправленное письмо Касьяна" },
    description: {
      en: "Draft letter never sent, private tone, unfinished.",
      ru: "Черновик письма, так и не отправленный, личный тон, незакончен.",
    },
    type: "documentary",
    location_id: "iron_lodge_common_room",
  },
  hallway_confrontation: {
    name: { en: "Witness Account: Afternoon Confrontation", ru: "Показания: дневная стычка" },
    description: {
      en: "Account of a public confrontation involving Elena earlier that day.",
      ru: "Описание публичной стычки с участием Елены днём.",
    },
    type: "testimonial",
    location_id: "third_floor_corridor",
  },
  magnus_order: {
    name: { en: "Torn Parchment Fragment", ru: "Рваный фрагмент пергамента" },
    description: {
      en: "Fragment of an order in a powerful hand, protection language.",
      ru: "Фрагмент приказа твёрдой рукой, формулировки о защите.",
    },
    type: "documentary",
    location_id: "third_floor_corridor",
  },
  prefect_patrol_notes: {
    name: { en: "Prefect Patrol Schedule", ru: "Расписание патруля префектов" },
    description: {
      en: "Who was supposed to be where on the upper floors that night.",
      ru: "Кто где должен был быть на верхних этажах той ночью.",
    },
    type: "documentary",
    location_id: "third_floor_corridor",
  },
  healing_supplies: {
    name: { en: "Wisp's Healing Supplies", ru: "Целебные припасы Жихаря Тихона" },
    description: {
      en: "Carefully kept remedies and bandages in the kitchen stores.",
      ru: "Аккуратно сложенные травы и бинты, спрятанные среди кухонных припасов.",
    },
    type: "physical",
    location_id: "kitchens",
  },
  kitchen_log: {
    name: { en: "Kitchen Duty Log", ru: "Журнал кухонной смены" },
    description: {
      en: "Duty log showing an absence window during the attack hour.",
      ru: "Журнал смены с окном отсутствия в час нападения.",
    },
    type: "documentary",
    location_id: "kitchens",
  },
  wisp_frostbite: {
    name: { en: "Wisp's Frostbitten Hands", ru: "Обмороженные руки Жихаря Тихона" },
    description: {
      en: "Physical frost injury on a bound familiar's hands.",
      ru: "Обморожения на руках приписного жихаря; след холода ещё не сошёл.",
    },
    type: "physical",
    location_id: "kitchens",
  },
  familiar_duty_roster: {
    name: { en: "Bound-Familiar Duty Roster", ru: "Расписание смен приписных домовых" },
    description: {
      en: "Roster of kitchen and hall duties for bound familiars.",
      ru: "Расписание кухонных и зальных смен домовых, прикреплённых к Чернолесью.",
    },
    type: "documentary",
    location_id: "kitchens",
  },
};

export const WITNESS_CATALOG: Record<WitnessId, WitnessCatalogEntry> = {
  elena: {
    name: WITNESS_NAMES.elena,
    bio: {
      en: "Brilliant Scarlet Court student. Speaks quickly when nervous. Present in the sealed archive that night.",
      ru: "Блестящая ученица Алого двора. Говорит быстро, когда нервничает. В ту ночь была в опечатанной библиотеке.",
    },
  },
  cassian: {
    name: WITNESS_NAMES.cassian,
    bio: {
      en: "Iron Lodge heir under heavy family pressure. Proud, brittle, and terrified of failure.",
      ru: "Наследник Железного двора под давлением семьи. Гордый, напуганный, боится провала.",
    },
  },
  whitmore: {
    name: WITNESS_NAMES.whitmore,
    bio: {
      en: "Professor Minerva Whitmore, senior staff, sharp observer of college politics.",
      ru: "Профессор Мирослава Витязева, старший состав, острый наблюдатель политики коллегии.",
    },
  },
  wisp: {
    name: WITNESS_NAMES.wisp,
    bio: {
      en: "Bound familiar of the Thorne household. Works the kitchens. Speaks of himself in the third person.",
      ru: "Приписной домовой семьи Тернских. Работает на кухне, называет себя в третьем лице и прячет руки в рукавах.",
    },
  },
};

/**
 * All 7 engine rites (6 safe + 1 restricted).
 * Help text includes cast examples that match spell detection phrases.
 * IDs must match backend SPELL_DEFINITIONS.
 */
export const RITES: RiteCatalogEntry[] = [
  {
    id: "unveil",
    name: { en: "Unveil", ru: "Снять покров" },
    help: {
      en: "Reveal hidden writing, concealments, true form. Chat: “unveil the desk” / “reveal hidden marks on the note”.",
      ru: "Открывает скрытые записи, маскировку и истинный вид вещей. Например: «сними покров со стола» или «покажи скрытые знаки на записке».",
    },
  },
  {
    id: "sense_presence",
    name: { en: "Sense Presence", ru: "Ощутить присутствие" },
    help: {
      en: "Feel if someone is near, even through walls. Chat: “sense presence” / “detect people nearby”.",
      ru: "Помогает понять, есть ли кто-то рядом, даже за стеной. Например: «почувствуй присутствие» или «кто-нибудь есть поблизости?».",
    },
  },
  {
    id: "identify_substance",
    name: { en: "Identify Substance", ru: "Опознать вещество" },
    help: {
      en: "Read potions, poisons, cursed matter. Chat: “identify substance on the residue” / “identify potion”.",
      ru: "Определяет зелья, яды и следы проклятий. Например: «опознай вещество на ткани» или «что это за зелье?».",
    },
  },
  {
    id: "raise_the_lamp",
    name: { en: "Raise the Lamp", ru: "Поднять лампу" },
    help: {
      en: "Investigative light, blood, scorch, what hides in shadow. Chat: “raise the lamp” / “illuminate the alcove”.",
      ru: "Выявляет кровь, ожоги и то, что прячется в тени. Например: «подними лампу» или «освети нишу».",
    },
  },
  {
    id: "echo_reading",
    name: { en: "Echo Reading", ru: "Чтение эха" },
    help: {
      en: "Last spells on a focus in hand. Chat: “echo reading on the focus” / “last spell on his focus”.",
      ru: "Показывает последние чары на фокусе. Например: «прочитай эхо на фокусе» или «какое заклинание он применил последним?».",
    },
  },
  {
    id: "mend",
    name: { en: "Mend", ru: "Починить" },
    help: {
      en: "Restore a broken object; watch how it broke. Chat: “mend this glass” / “repair this”.",
      ru: "Собирает разбитую вещь и оставляет подсказки о том, как она сломалась. Например: «почини стекло».",
    },
  },
  {
    id: "mnemonic_delving",
    name: { en: "Mnemonic Delving", ru: "Погружение в память" },
    help: {
      en: "Restricted. Probe a mind for memory, costly, detected if clumsy. Chat: “read her mind about the archive” / “mnemonic delving on Elena”.",
      ru: "Запретный обряд. Позволяет заглянуть в чужие воспоминания, но неосторожность заметят. Например: «взгляни в память Елены о происшествии».",
    },
  },
];

export function pick(lang: Language, text: LocalizedText): string {
  return lang === "ru" ? text.ru : text.en;
}

export function locationName(lang: Language, id: string): string {
  if ((LOCATION_IDS as readonly string[]).includes(id)) {
    const n = LOCATION_NAMES[id as LocationId];
    return lang === "ru" ? n.ru : n.en;
  }
  return id;
}

export function witnessName(lang: Language, id: string): string {
  if ((WITNESS_IDS as readonly string[]).includes(id)) {
    return pick(lang, WITNESS_CATALOG[id as WitnessId].name);
  }
  return id;
}

export function evidenceDisplay(
  lang: Language,
  id: string,
): { name: string; description: string; type: string; location_id: string; location_name: string } {
  const e = EVIDENCE_CATALOG[id];
  if (!e) {
    return {
      name: id,
      description: "",
      type: "unknown",
      location_id: "",
      location_name: "",
    };
  }
  return {
    name: pick(lang, e.name),
    description: pick(lang, e.description),
    type: e.type,
    location_id: e.location_id,
    location_name: locationName(lang, e.location_id),
  };
}

/** Completeness: every EN key has RU; catalog IDs stable. */
export function assertCaseCatalogParity(): void {
  const check = (obj: LocalizedText, path: string) => {
    if (!obj.en?.trim()) throw new Error(`missing en: ${path}`);
    if (!obj.ru?.trim()) throw new Error(`missing ru: ${path}`);
  };
  check(CASE_META.title, "title");
  check(CASE_META.synopsis, "synopsis");
  for (const [id, e] of Object.entries(EVIDENCE_CATALOG)) {
    check(e.name, `evidence.${id}.name`);
    check(e.description, `evidence.${id}.description`);
  }
  for (const id of WITNESS_IDS) {
    check(WITNESS_CATALOG[id].name, `witness.${id}.name`);
    check(WITNESS_CATALOG[id].bio, `witness.${id}.bio`);
  }
  for (const r of RITES) {
    check(r.name, `rite.${r.id}.name`);
    check(r.help, `rite.${r.id}.help`);
  }
}
