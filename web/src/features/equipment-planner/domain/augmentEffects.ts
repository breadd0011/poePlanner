import type { AugmentEffect, EditorModifier, PlannerAugment } from "../../../types";

export type AppliedAugmentEffectLine = {
  id: string;
  augmentId: string | null;
  augmentName: string | null;
  condition: string | null;
  label: string | null;
  text: string;
};

export type AugmentLookupIndex = {
  byId: Map<string, PlannerAugment>;
  byUrl: Map<string, PlannerAugment>;
  byName: Map<string, PlannerAugment>;
};

const ALL_EQUIPMENT_CONDITION = "all_equipment";

const MARTIAL_WEAPON_CLASSES = new Set([
  "bows",
  "claws",
  "crossbows",
  "daggers",
  "flails",
  "one hand axes",
  "one hand maces",
  "one hand swords",
  "quarterstaves",
  "spears",
  "two hand axes",
  "two hand maces",
  "two hand swords",
]);

const WAND_OR_STAFF_CLASSES = new Set(["staves", "wands"]);

const ARMOUR_CLASSES = new Set([
  "body armours",
  "boots",
  "foci",
  "gloves",
  "helmets",
  "shields",
]);

const DIRECT_ITEM_CLASS_CONDITIONS: Record<string, string[]> = {
  "body armours": ["body_armours", "body_armour"],
  boots: ["boots"],
  bucklers: ["bucklers", "shields_bucklers", "shields_or_bucklers"],
  foci: ["foci", "focus"],
  gloves: ["gloves"],
  helmets: ["helmets"],
  quivers: ["quivers", "quiver"],
  sceptres: ["sceptres", "sceptre"],
  shields: ["shields", "shields_bucklers", "shields_or_bucklers"],
};

function normalizeToken(value: string | null | undefined): string {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function normalizeUrl(value: string | null | undefined): string {
  return (value ?? "").trim().replace(/#.*$/, "").replace(/\/$/, "");
}

export function normalizeAugmentName(value: string | null | undefined): string {
  return normalizeToken(value);
}

export function normalizeAugmentCondition(value: string | null | undefined): string {
  const normalized = normalizeToken(value);
  if (!normalized) return "";
  if (normalized === "martial weapon" || normalized === "martial weapons") return "martial_weapon";
  if (normalized === "wand or staff" || normalized === "wand staff" || normalized === "wands staves") return "wand_or_staff";
  if (normalized === "armour" || normalized === "armor") return "armour";
  if (normalized === "all equipment" || normalized === "equipment") return ALL_EQUIPMENT_CONDITION;
  if (normalized === "shields bucklers" || normalized === "shields and bucklers" || normalized === "shield buckler") return "shields_bucklers";
  return normalized.replace(/\s+/g, "_");
}

export function normalizeItemClassName(value: string | null | undefined): string {
  return normalizeToken(value);
}

export function createAugmentLookupIndex(augments: PlannerAugment[]): AugmentLookupIndex {
  const byId = new Map<string, PlannerAugment>();
  const byUrl = new Map<string, PlannerAugment>();
  const byName = new Map<string, PlannerAugment>();

  for (const augment of augments) {
    if (augment.id) byId.set(augment.id, augment);
    const sourceUrl = normalizeUrl(augment.sourceUrl);
    if (sourceUrl && !byUrl.has(sourceUrl)) byUrl.set(sourceUrl, augment);
    const name = normalizeAugmentName(augment.name);
    if (name && !byName.has(name)) byName.set(name, augment);
  }

  return { byId, byUrl, byName };
}

function isAugmentLookupIndex(value: AugmentLookupIndex | PlannerAugment[]): value is AugmentLookupIndex {
  return !Array.isArray(value);
}

function asAugmentLookupIndex(value: AugmentLookupIndex | PlannerAugment[]): AugmentLookupIndex {
  return isAugmentLookupIndex(value) ? value : createAugmentLookupIndex(value);
}

export function augmentConditionForItemClass(itemClass: string): string | null {
  const normalizedItemClass = normalizeItemClassName(itemClass);
  if (MARTIAL_WEAPON_CLASSES.has(normalizedItemClass)) return "martial_weapon";
  if (WAND_OR_STAFF_CLASSES.has(normalizedItemClass)) return "wand_or_staff";
  if (ARMOUR_CLASSES.has(normalizedItemClass)) return "armour";
  return null;
}

function augmentConditionsForItemClass(itemClass: string): string[] {
  const normalizedItemClass = normalizeItemClassName(itemClass);
  const conditions = new Set<string>();
  const broad = augmentConditionForItemClass(itemClass);
  if (broad) conditions.add(broad);
  for (const condition of DIRECT_ITEM_CLASS_CONDITIONS[normalizedItemClass] ?? []) {
    conditions.add(condition);
  }
  conditions.add(ALL_EQUIPMENT_CONDITION);
  return Array.from(conditions);
}

export function findAugmentForSocketModifier(
  mod: EditorModifier,
  lookup: AugmentLookupIndex | PlannerAugment[],
): PlannerAugment | null {
  if (mod.sourceMechanic !== "augment") return null;
  const index = asAugmentLookupIndex(lookup);
  if (mod.augmentId) {
    const byId = index.byId.get(mod.augmentId);
    if (byId) return byId;
  }

  const sourceUrl = normalizeUrl(mod.augmentSourceUrl ?? mod.sourceUrl);
  if (sourceUrl) {
    const byUrl = index.byUrl.get(sourceUrl);
    if (byUrl) return byUrl;
  }

  const augmentName = normalizeAugmentName(mod.augmentName ?? mod.runeName);
  return augmentName ? (index.byName.get(augmentName) ?? null) : null;
}

export function resolveSocketAugmentsForMods(
  socketMods: EditorModifier[],
  lookup: AugmentLookupIndex | PlannerAugment[],
): Array<PlannerAugment | null> {
  const index = asAugmentLookupIndex(lookup);
  return socketMods.map((mod) => findAugmentForSocketModifier(mod, index));
}

function normalEffect(effect: AugmentEffect): boolean {
  return !effect.bonded;
}

function effectMatchesCondition(effect: AugmentEffect, condition: string): boolean {
  return normalizeAugmentCondition(effect.condition) === condition;
}

function effectForCondition(
  augment: PlannerAugment | null,
  conditions: string[],
): AugmentEffect | null {
  if (!augment) return null;
  const normalEffects = augment.augmentEffects.filter(normalEffect);
  for (const condition of conditions.filter((value) => value !== ALL_EQUIPMENT_CONDITION)) {
    const effect = normalEffects.find((candidate) => effectMatchesCondition(candidate, condition));
    if (effect) return effect;
  }
  return (
    normalEffects.find((effect) =>
      effectMatchesCondition(effect, ALL_EQUIPMENT_CONDITION),
    ) ?? null
  );
}

function fallbackSocketText(mod: EditorModifier): string {
  return mod.socketStatText ?? mod.textTemplate ?? mod.displayRangeText ?? mod.text;
}

export function socketModifierAppliesToItemClass({
  itemClass,
  mod,
  lookup,
}: {
  itemClass: string;
  mod: EditorModifier;
  lookup: AugmentLookupIndex | PlannerAugment[];
}): boolean {
  if (mod.sourceMechanic !== "augment") return true;
  const augment = findAugmentForSocketModifier(mod, lookup);
  if (!augment) return false;
  if (!augment.augmentEffects.length) return false;
  return Boolean(effectForCondition(augment, augmentConditionsForItemClass(itemClass)));
}

export function resolveAppliedAugmentEffectsForItem({
  itemClass,
  socketMods,
  lookup,
  augments,
}: {
  itemClass: string;
  socketMods: EditorModifier[];
  lookup?: AugmentLookupIndex | PlannerAugment[];
  augments?: PlannerAugment[];
}): AppliedAugmentEffectLine[] {
  const conditions = augmentConditionsForItemClass(itemClass);
  const index = asAugmentLookupIndex(lookup ?? augments ?? []);

  return socketMods
    .map((mod, indexInSocketList) => {
      const augment = findAugmentForSocketModifier(mod, index);
      const effect = effectForCondition(augment, conditions);
      const text = effect?.text ?? fallbackSocketText(mod);
      if (!text.trim()) return null;

      const line: AppliedAugmentEffectLine = {
        id: `applied-augment:${mod.id}:${indexInSocketList}`,
        augmentId: augment?.id ?? null,
        augmentName: augment?.name ?? mod.augmentName ?? mod.runeName ?? null,
        condition: effect ? normalizeAugmentCondition(effect.condition) : (conditions[0] ?? null),
        label: effect?.label ?? null,
        text,
      };
      return line;
    })
    .filter((line): line is AppliedAugmentEffectLine => Boolean(line));
}
