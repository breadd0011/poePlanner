import type { PlannerAugment, PlannerPocData } from "../../../types";

export const RARITIES = ["Normal", "Magic", "Rare", "Unique"] as const;
export type Rarity = (typeof RARITIES)[number];
export type ItemClassOption = string;

export type ItemOption = {
  id: string;
  kind: "base" | "unique";
  itemClass: ItemClassOption;
  label: string;
  name: string;
  baseName: string;
  subtype: string;
  uniqueId?: string;
  icon?: string | null;
  compatibleSlots?: string[];
  socketCapacity?: number | null;
  searchText?: string | null;
};

export type SlotKey =
  | "helmet"
  | "amulet"
  | "weapon1"
  | "body"
  | "gloves"
  | "ring1"
  | "belt"
  | "ring2"
  | "boots"
  | "weapon2"
  | "lifeFlask"
  | "manaFlask"
  | "charm1"
  | "charm2"
  | "charm3";

export type EquipmentSlotDef = {
  id: SlotKey;
  label: string;
  left: string;
  top: string;
  width: string;
  height: string;
  hasTabs?: boolean;
  tone?: "default" | "life" | "mana";
};

type EquipmentSlotLayoutDef = Omit<
  EquipmentSlotDef,
  "left" | "top" | "width" | "height"
> & {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type EquippedItemDraft = {
  customName: string;
  customValues: Record<string, Record<number, string>>;
  isCorrupted: boolean;
  isSanctified: boolean;
  itemLevel: number;
  quality: number;
  rarity: Rarity;
  selectedBaseName: string;
  selectedIds: string[];
  selectedItemClass: string;
  selectedItemId: string;
  selectedSubtypeKey: string;
  selectedUniqueId: string;
  socketCount: number;
};

export type EquippedPreview = {
  name: string;
  baseName: string;
  itemClass: string;
  rarity: Rarity;
  icon?: string | null;
  socketCapacity?: number;
  socketFilledCount?: number;
  socketAugments?: Array<PlannerAugment | null>;
  draft?: EquippedItemDraft;
};

export const EQUIPMENT_BOARD_LAYOUT = {
  width: 924,
  height: 689,
} as const;

function toLayoutPercent(value: number, total: number): string {
  return `${Number(((value / total) * 100).toFixed(4))}%`;
}

function fromLayoutSlot(def: EquipmentSlotLayoutDef): EquipmentSlotDef {
  const { x, y, ...slot } = def;

  return {
    ...slot,
    left: toLayoutPercent(x, EQUIPMENT_BOARD_LAYOUT.width),
    top: toLayoutPercent(y, EQUIPMENT_BOARD_LAYOUT.height),
    width: toLayoutPercent(def.width, EQUIPMENT_BOARD_LAYOUT.width),
    height: toLayoutPercent(def.height, EQUIPMENT_BOARD_LAYOUT.height),
  };
}

export const equipmentSlotLayout: EquipmentSlotLayoutDef[] = [
  {
    x: 86,
    y: 36,
    width: 172,
    height: 314,
    id: "weapon1",
    label: "Weapon Slot 1",
    hasTabs: true,
  },
  {
    x: 668,
    y: 36,
    width: 172,
    height: 314,
    id: "weapon2",
    label: "Weapon Slot 2",
    hasTabs: true,
  },

  {
    x: 376,
    y: 20,
    width: 172,
    height: 162,
    id: "helmet",
    label: "Helmet",
  },
  {
    x: 376,
    y: 186,
    width: 172,
    height: 238,
    id: "body",
    label: "Body Armour",
  },
  { x: 377, y: 428, width: 172, height: 88, id: "belt", label: "Belt" },

  {
    x: 194,
    y: 354,
    width: 172,
    height: 164,
    id: "gloves",
    label: "Gloves",
  },

  { x: 560, y: 354, width: 172, height: 164, id: "boots", label: "Boots" },

  { x: 564, y: 170, width: 88, height: 88, id: "amulet", label: "Amulet" },
  { x: 564, y: 262, width: 88, height: 88, id: "ring2", label: "Ring" },
  { x: 272, y: 262, width: 88, height: 88, id: "ring1", label: "Ring" },

  {
    x: 231,
    y: 514,
    width: 114,
    height: 170,
    id: "lifeFlask",
    label: "Life Flask",
    tone: "life",
  },
  {
    x: 590,
    y: 514,
    width: 114,
    height: 170,
    id: "manaFlask",
    label: "Mana Flask",
    tone: "mana",
  },

  { x: 498, y: 557, width: 81, height: 79, id: "charm3", label: "" },
  { x: 426, y: 557, width: 81, height: 79, id: "charm2", label: "" },
  { x: 354, y: 557, width: 81, height: 79, id: "charm1", label: "" },
];

export const equipmentSlots: EquipmentSlotDef[] =
  equipmentSlotLayout.map(fromLayoutSlot);

const weaponItemClasses = [
  "Bows",
  "Crossbows",
  "Wands",
  "Sceptres",
  "Daggers",
  "Claws",
  "Quarterstaves",
  "Staves",
  "One Hand Swords",
  "Two Hand Swords",
  "One Hand Axes",
  "Two Hand Axes",
  "One Hand Maces",
  "Two Hand Maces",
  "Spears",
  "Flails",
  "Talismans",
] as const;

const offhandItemClasses = ["Shields", "Foci", "Quivers"] as const;

export type SlotCompatibilityMap = Readonly<Partial<Record<SlotKey, ReadonlySet<string>>>>;

type RecordLike = Record<string, unknown>;

const DEFAULT_SLOT_COMPATIBILITY: Record<SlotKey, string[]> = {
  helmet: ["Helmets"],
  amulet: ["Amulets"],
  weapon1: [...weaponItemClasses],
  body: ["Body Armours"],
  gloves: ["Gloves"],
  ring1: ["Rings"],
  belt: ["Belts"],
  ring2: ["Rings"],
  boots: ["Boots"],
  weapon2: [...weaponItemClasses, ...offhandItemClasses],
  lifeFlask: ["Life Flasks", "Life Flask"],
  manaFlask: ["Mana Flasks", "Mana Flask"],
  charm1: ["Charms"],
  charm2: ["Charms"],
  charm3: ["Charms"],
};

function isRecord(value: unknown): value is RecordLike {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isSlotKey(value: unknown): value is SlotKey {
  return typeof value === "string" && equipmentSlots.some((slot) => slot.id === value);
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string" && Boolean(entry.trim()));
}

function buildCompatibilityMap(entries: Array<[SlotKey, string[]]>): SlotCompatibilityMap {
  return Object.fromEntries(
    entries.map(([slot, itemClasses]) => [slot, new Set(itemClasses)]),
  ) as SlotCompatibilityMap;
}

const DEFAULT_SLOT_COMPATIBILITY_MAP = buildCompatibilityMap(
  Object.entries(DEFAULT_SLOT_COMPATIBILITY) as Array<[SlotKey, string[]]>,
);

function compatibilityEntriesFromRecord(value: unknown): Array<[SlotKey, string[]]> {
  if (!isRecord(value)) return [];
  return Object.entries(value).flatMap(([slot, itemClasses]) => {
    if (!isSlotKey(slot)) return [];
    const classes = stringList(itemClasses);
    return classes.length ? [[slot, classes] as [SlotKey, string[]]] : [];
  });
}

function compatibilityEntriesFromArray(value: unknown): Array<[SlotKey, string[]]> {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (!isRecord(entry)) return [];
    const slot = entry.slot ?? entry.id;
    if (!isSlotKey(slot)) return [];
    const itemClasses =
      stringList(entry.itemClasses).length ? stringList(entry.itemClasses) :
      stringList(entry.acceptsItemClasses).length ? stringList(entry.acceptsItemClasses) :
      stringList(entry.compatibleItemClasses);
    return itemClasses.length ? [[slot, itemClasses] as [SlotKey, string[]]] : [];
  });
}

function configuredCompatibilitySources(data: PlannerPocData): unknown[] {
  return [
    data.ui?.itemEditor?.slotCompatibility,
    data.ui?.itemEditor?.equipmentSlots,
    data.ui?.slotCompatibility,
    data.ui?.equipmentSlots,
    data.slotCompatibility,
    data.equipmentSlots,
  ];
}

export function createSlotCompatibilityMap(data?: PlannerPocData): SlotCompatibilityMap {
  if (!data) return DEFAULT_SLOT_COMPATIBILITY_MAP;

  for (const source of configuredCompatibilitySources(data)) {
    const entries = Array.isArray(source)
      ? compatibilityEntriesFromArray(source)
      : compatibilityEntriesFromRecord(source);
    if (entries.length) return buildCompatibilityMap(entries);
  }

  return DEFAULT_SLOT_COMPATIBILITY_MAP;
}

export function getSlotLabel(id: SlotKey): string {
  if (id === "charm1" || id === "charm2" || id === "charm3") return "Charm";
  return equipmentSlots.find((slot) => slot.id === id)?.label ?? "Slot";
}

export function slotAcceptsItemClass(
  slot: SlotKey,
  itemClass: string,
  compatibility: SlotCompatibilityMap = DEFAULT_SLOT_COMPATIBILITY_MAP,
): boolean {
  return Boolean(compatibility[slot]?.has(itemClass));
}

export function slotAcceptsOption(
  slot: SlotKey,
  option: ItemOption,
  compatibility?: SlotCompatibilityMap,
): boolean {
  if (option.compatibleSlots?.length) return option.compatibleSlots.includes(slot);
  return slotAcceptsItemClass(slot, option.itemClass, compatibility);
}
