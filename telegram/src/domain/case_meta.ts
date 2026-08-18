/** Canonical Case 1 IDs, never translate IDs. */

export const CASE_001 = "case_001" as const;

export const LOCATION_IDS = [
  "library",
  "iron_lodge_common_room",
  "third_floor_corridor",
  "kitchens",
] as const;

export type LocationId = (typeof LOCATION_IDS)[number];

export const WITNESS_IDS = ["elena", "cassian", "whitmore", "wisp"] as const;

export type WitnessId = (typeof WITNESS_IDS)[number];

/** Suspects for verdict mock selector (same cast). */
export const SUSPECT_IDS = WITNESS_IDS;

export const LOCATION_NAMES: Record<
  LocationId,
  { en: string; ru: string; description_en: string; description_ru: string }
> = {
  library: {
    en: "Sealed Archive",
    ru: "Опечатанная библиотека",
    description_en:
      "Frost spreads across the windows from inside. Beyond the towering shelves, an eastern alcove hides a reading desk and the professor's frozen body.",
    description_ru:
      "Иней ползёт по стёклам изнутри. За высокими стеллажами скрыты восточная ниша, читальный стол и застывшее тело профессора.",
  },
  iron_lodge_common_room: {
    en: "Iron Lodge Common Room",
    ru: "Гостиная Железного двора",
    description_en:
      "The common room of Blackwood's old Iron Lodge house: green lake-light, a dying fire, locked trunks, and letters from ambitious heirs.",
    description_ru:
      "Гостиная старого Железного двора: зелёный отсвет в окнах, догорающий камин, запертые сундуки и письма честолюбивых наследников.",
  },
  third_floor_corridor: {
    en: "Third Floor Corridor",
    ru: "Коридор третьего этажа",
    description_en:
      "Upper corridor of Blackwood Collegiate, stone, portraits, doors that remember footsteps.",
    description_ru:
      "Верхний коридор Чернолесской коллегии, камень, портреты и двери, помнящие чужие шаги.",
  },
  kitchens: {
    en: "Blackwood Collegiate Kitchens",
    ru: "Кухни Чернолесской коллегии",
    description_en:
      "Bound-familiar kitchens below the hall, steam, logs, duty rosters, and quiet work.",
    description_ru:
      "Кухни под Большой палатой: пар, медные котлы, журналы смен и тихая работа приписных домовых.",
  },
};

/** Offline fallback only; live Telegram text comes from localized engine snapshots. */
export function locationCopy(
  id: string,
  lang: "en" | "ru",
): { name: string; description: string } {
  if (!isLocationId(id)) {
    return { name: id, description: "" };
  }
  const m = LOCATION_NAMES[id];
  return {
    name: lang === "ru" ? m.ru : m.en,
    description: lang === "ru" ? m.description_ru : m.description_en,
  };
}

export const WITNESS_NAMES: Record<WitnessId, { en: string; ru: string }> = {
  elena: { en: "Elena Marsh", ru: "Елена Лозовская" },
  cassian: { en: "Cassian Thorne", ru: "Касьян Тернский" },
  whitmore: { en: "Professor Minerva Whitmore", ru: "Профессор Мирослава Витязева" },
  wisp: { en: "Wisp", ru: "Жихарь Тихон" },
};

export const CASE_COVER = {
  en: {
    title: "The Sealed Archive",
    body:
      "Professor Aldric Vane lies frozen in Blackwood's sealed archive. Three suspects, two thefts, and a spell no one will claim. The first answer looks obvious. That is why it cannot be trusted.\n\n" +
      "Blackwood Collegiate, autumn 1890. The Crown Bureau of Supernatural Investigations has sent you, an investigator of the Lantern Order, its field service for cases ordinary constables cannot touch.",
  },
  ru: {
    title: "Опечатанная библиотека",
    body:
      "Профессор Аркадий Вежин застыл в опечатанной библиотеке Чернолесской коллегии. Трое подозреваемых, две кражи, два следа чар, и ни одного признания. Самый простой ответ слишком хорошо ложится на руку.\n\n" +
      "Чернолесская коллегия, осень 1890 года. Тайный приказ направил вас расследовать дело; в поле вас ведёт Орден Светоча, служба для происшествий, о которых обычным властям лучше не знать.",
  },
};

export function isLocationId(id: string): id is LocationId {
  return (LOCATION_IDS as readonly string[]).includes(id);
}

export function isWitnessId(id: string): id is WitnessId {
  return (WITNESS_IDS as readonly string[]).includes(id);
}

/** Asset relative paths under frontend/public (webp preferred). */
export function locationImageRel(id: LocationId): string {
  return `locations/${id}.webp`;
}

export function witnessImageRel(id: WitnessId): string {
  return `portraits/${id}.webp`;
}
