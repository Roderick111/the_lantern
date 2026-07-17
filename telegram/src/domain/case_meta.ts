/** Canonical Case 1 IDs — never translate IDs. */

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
    ru: "Запечатанный архив",
    description_en:
      "Frost spreads across the windows from inside. Beyond the towering shelves, an eastern alcove hides a reading desk and the professor's frozen body.",
    description_ru:
      "Иней расползается по окнам изнутри. За высокими стеллажами скрыты восточная ниша, читальный стол и застывшее тело профессора.",
  },
  iron_lodge_common_room: {
    en: "Iron Lodge Common Room",
    ru: "Гостиная Железного дома",
    description_en:
      "The common room of Blackwood's old Iron Lodge house: green lake-light, a dying fire, locked trunks, and letters from ambitious heirs.",
    description_ru:
      "Гостиная старого Железного дома: зелёный свет из-под воды, почти погасший камин, запертые сундуки и письма наследников.",
  },
  third_floor_corridor: {
    en: "Third Floor Corridor",
    ru: "Коридор третьего этажа",
    description_en:
      "Upper corridor of Blackwood Collegiate — stone, portraits, doors that remember footsteps.",
    description_ru:
      "Верхний коридор Блэквудского колледжа — камень, портреты, двери, помнящие шаги.",
  },
  kitchens: {
    en: "Blackwood Collegiate Kitchens",
    ru: "Кухни Блэквудского колледжа",
    description_en:
      "Bound-familiar kitchens below the hall — steam, logs, duty rosters, and quiet work.",
    description_ru:
      "Кухни под главным залом: пар, медные котлы, журналы смен и тихая работа фамильяров.",
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
  elena: { en: "Elena Marsh", ru: "Елена Марш" },
  cassian: { en: "Cassian Thorne", ru: "Кассиан Торн" },
  whitmore: { en: "Professor Minerva Whitmore", ru: "Профессор Минерва Уитмор" },
  wisp: { en: "Wisp", ru: "Висп" },
};

export const CASE_COVER = {
  en: {
    title: "The Sealed Archive",
    body:
      "Professor Aldric Vane lies frozen in Blackwood's sealed archive. Three suspects, two thefts, and a spell no one will claim. The first answer looks obvious. That is why it cannot be trusted.\n\n" +
      "Blackwood Collegiate, autumn 1890. The Crown Bureau of Supernatural Investigations has sent you — an investigator of the Lantern Order, its field service for cases ordinary constables cannot touch.",
  },
  ru: {
    title: "Запечатанный архив",
    body:
      "Профессор Олдрик Вейн застыл в библиотечном архиве Блэквуда. Трое подозреваемых, две кражи и заклинание, которое никто не признаёт своим. Первый ответ кажется очевидным. Поэтому доверять ему нельзя.\n\n" +
      "Блэквудский колледж, осень 1890 года. Вас направило Королевское бюро сверхъестественных расследований — в поле вас ведёт Орден Светочей, его служба для дел, до которых обычная полиция не добирается.",
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
