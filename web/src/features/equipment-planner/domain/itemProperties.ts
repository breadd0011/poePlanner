import type { BaseItemSummary, EditableValueRange, EditorModifier, UniqueItem } from "../../../types";
import {
  type CustomValueState,
  displayKey,
  formatNumber,
  getEditableValues,
  parseInlineRanges,
  renderModifierText,
  renderUniqueModText,
} from "./itemText";
import type { NumericRange } from "./itemDefences";

export type ItemPropertyKey =
  | "physicalDamage"
  | "fireDamage"
  | "coldDamage"
  | "lightningDamage"
  | "chaosDamage"
  | "criticalHitChance"
  | "attacksPerSecond"
  | "weaponRange"
  | "reloadTime"
  | "spirit"
  | "blockChance"
  | "baseMovementSpeed"
  | string;

export type CalculatedItemPropertyLine = {
  key: ItemPropertyKey;
  label: string;
  value: string;
  augmented: boolean;
  source: "calculated" | "base";
};

type DamageRange = NumericRange;

type WeaponContributions = {
  physicalFlat: DamageRange;
  physicalPercent: NumericRange;
  elementalFlat: Record<"fire" | "cold" | "lightning" | "chaos", DamageRange>;
  attackSpeedPercent: NumericRange;
  criticalChancePercent: NumericRange;
  criticalChanceFlat: NumericRange;
  spiritFlat: NumericRange;
  blockChanceFlat: NumericRange;
  blockChancePercent: NumericRange;
};

function emptyRange(): NumericRange {
  return { min: 0, max: 0 };
}

function emptyWeaponContributions(): WeaponContributions {
  return {
    physicalFlat: emptyRange(),
    physicalPercent: emptyRange(),
    elementalFlat: {
      fire: emptyRange(),
      cold: emptyRange(),
      lightning: emptyRange(),
      chaos: emptyRange(),
    },
    attackSpeedPercent: emptyRange(),
    criticalChancePercent: emptyRange(),
    criticalChanceFlat: emptyRange(),
    spiritFlat: emptyRange(),
    blockChanceFlat: emptyRange(),
    blockChancePercent: emptyRange(),
  };
}

function addRange(target: NumericRange, value: NumericRange) {
  target.min += value.min;
  target.max += value.max;
}

function coerceNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.replace("%", ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function coerceDamageRange(value: unknown): DamageRange | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as { min?: unknown; max?: unknown };
  const min = coerceNumber(raw.min);
  const max = coerceNumber(raw.max);
  if (min === null || max === null) return null;
  return { min, max };
}

function parseBlockChance(value: unknown): number | null {
  if (typeof value === "string") return coerceNumber(value);
  return coerceNumber(value);
}

function propertyKeyFromLine(line: string): ItemPropertyKey {
  const label = line.split(":")[0]?.trim().toLowerCase() ?? line.toLowerCase();
  if (label === "physical damage") return "physicalDamage";
  if (label === "fire damage") return "fireDamage";
  if (label === "cold damage") return "coldDamage";
  if (label === "lightning damage") return "lightningDamage";
  if (label === "chaos damage") return "chaosDamage";
  if (label === "critical hit chance") return "criticalHitChance";
  if (label === "attacks per second") return "attacksPerSecond";
  if (label === "weapon range") return "weaponRange";
  if (label === "reload time") return "reloadTime";
  if (label === "spirit") return "spirit";
  if (label === "block chance") return "blockChance";
  if (label === "base movement speed") return "baseMovementSpeed";
  return label.replace(/[^a-z0-9]+(.)/g, (_, chr: string) => chr.toUpperCase());
}

function rangeFromEditableValue(
  range: EditableValueRange,
  raw: string | undefined,
): NumericRange | null {
  const override = raw?.trim();
  if (override) {
    const parsed = Number(override);
    if (Number.isFinite(parsed)) return { min: parsed, max: parsed };
  }
  if (range.value !== null && Number.isFinite(range.value)) {
    return { min: range.value, max: range.value };
  }
  if (range.min !== null && range.max !== null) {
    return {
      min: Math.min(range.min, range.max),
      max: Math.max(range.min, range.max),
    };
  }
  return null;
}

function editableRanges(
  mod: EditorModifier,
  customValues: CustomValueState,
): NumericRange[] {
  return getEditableValues(mod)
    .map((value) => rangeFromEditableValue(value, customValues[mod.id]?.[value.index]))
    .filter((value): value is NumericRange => Boolean(value));
}

function uniqueEditableRanges(
  mod: UniqueItem["explicitMods"][number],
  customValues: CustomValueState,
): NumericRange[] {
  return parseInlineRanges(mod.text)
    .map((value) => rangeFromEditableValue(value, customValues[mod.id]?.[value.index]))
    .filter((value): value is NumericRange => Boolean(value));
}

function firstNumberFromText(text: string): NumericRange | null {
  const match = text.match(/[+\-]?(?:\d+(?:\.\d+)?)/);
  if (!match) return null;
  const parsed = Number(match[0]);
  if (!Number.isFinite(parsed)) return null;
  return { min: parsed, max: parsed };
}

function firstTwoRangesFromText(text: string): NumericRange[] {
  const matches = [...text.matchAll(/[+\-]?(?:\d+(?:\.\d+)?)/g)]
    .map((match) => Number(match[0]))
    .filter((value) => Number.isFinite(value));
  if (matches.length < 2) return [];
  return [
    { min: matches[0], max: matches[0] },
    { min: matches[1], max: matches[1] },
  ];
}

function valueRangesForRenderedText(
  text: string,
  suppliedRanges: NumericRange[],
): NumericRange[] {
  if (suppliedRanges.length) return suppliedRanges;
  if (/adds\s+[+\-]?\d/i.test(text)) return firstTwoRangesFromText(text);
  const first = firstNumberFromText(text);
  return first ? [first] : [];
}

function affectsLocalItemProperty(text: string): boolean {
  const lower = text.toLowerCase();
  if (lower.includes("minion")) return false;
  if (lower.includes("ally") || lower.includes("allies")) return false;
  if (lower.includes("spell")) return false;
  if (lower.includes("skill")) return false;
  if (lower.includes("global")) return false;
  return true;
}

function applyContributionFromText(
  target: WeaponContributions,
  text: string,
  suppliedRanges: NumericRange[],
) {
  const ranges = valueRangesForRenderedText(text, suppliedRanges);
  if (!ranges.length) return;

  if (/adds\s+.+\s+to\s+.+\s+physical damage/i.test(text) && affectsLocalItemProperty(text)) {
    const [minRange, maxRange] = ranges;
    if (minRange && maxRange) {
      addRange(target.physicalFlat, {
        min: minRange.min,
        max: maxRange.max,
      });
    }
    return;
  }

  for (const element of ["fire", "cold", "lightning", "chaos"] as const) {
    const pattern = new RegExp(`adds\\s+.+\\s+to\\s+.+\\s+${element} damage`, "i");
    if (pattern.test(text) && affectsLocalItemProperty(text)) {
      const [minRange, maxRange] = ranges;
      if (minRange && maxRange) {
        addRange(target.elementalFlat[element], {
          min: minRange.min,
          max: maxRange.max,
        });
      }
      return;
    }
  }

  if (/%\s+increased\s+physical damage/i.test(text) && affectsLocalItemProperty(text)) {
    addRange(target.physicalPercent, ranges[0]);
    return;
  }

  if (/%\s+increased\s+attack speed/i.test(text) && affectsLocalItemProperty(text)) {
    addRange(target.attackSpeedPercent, ranges[0]);
    return;
  }

  if (/%\s+increased\s+critical hit chance/i.test(text) && affectsLocalItemProperty(text)) {
    addRange(target.criticalChancePercent, ranges[0]);
    return;
  }

  if (/to\s+critical hit chance/i.test(text) && /%/.test(text) && affectsLocalItemProperty(text)) {
    addRange(target.criticalChanceFlat, ranges[0]);
    return;
  }

  if (/to\s+spirit\b/i.test(text) || /^\s*[+\-]?(?:\d|#).*\bspirit\b/i.test(text)) {
    addRange(target.spiritFlat, ranges[0]);
    return;
  }

  if (/to\s+block chance/i.test(text) || /^\s*[+\-]?(?:\d|#).*\bblock chance\b/i.test(text)) {
    if (/%\s+increased/i.test(text)) {
      addRange(target.blockChancePercent, ranges[0]);
    } else {
      addRange(target.blockChanceFlat, ranges[0]);
    }
  }
}

function collectContributions(
  mods: EditorModifier[],
  uniqueMods: UniqueItem["explicitMods"],
  customValues: CustomValueState,
): WeaponContributions {
  const contributions = emptyWeaponContributions();
  for (const mod of mods) {
    applyContributionFromText(
      contributions,
      renderModifierText(mod, customValues),
      editableRanges(mod, customValues),
    );
  }
  for (const mod of uniqueMods) {
    applyContributionFromText(
      contributions,
      renderUniqueModText(mod, customValues),
      uniqueEditableRanges(mod, customValues),
    );
  }
  return contributions;
}

function formatRange(range: DamageRange): string {
  return `${formatNumber(Math.floor(range.min))}-${formatNumber(Math.floor(range.max))}`;
}

function formatDecimal(value: number, maxDigits = 2): string {
  return Number(value.toFixed(maxDigits)).toString();
}

function formatPercent(value: number): string {
  return `${formatDecimal(value, 2)}%`;
}

export function calculatePhysicalDamageRange({
  base,
  flat,
  percent,
  quality = 0,
}: {
  base: DamageRange;
  flat: DamageRange;
  percent: NumericRange;
  quality?: number;
}): DamageRange {
  const safeQuality = Math.max(0, Math.min(30, quality));
  const min = (base.min + flat.min) * (1 + percent.min / 100) * (1 + safeQuality / 100);
  const max = (base.max + flat.max) * (1 + percent.max / 100) * (1 + safeQuality / 100);
  return { min: Math.floor(min), max: Math.floor(max) };
}

export function calculatePercentScaledValue({
  base,
  percent,
  decimals = 2,
}: {
  base: number;
  percent: NumericRange;
  decimals?: number;
}): NumericRange {
  const multiplier = 10 ** decimals;
  return {
    min: Math.round(base * (1 + percent.min / 100) * multiplier) / multiplier,
    max: Math.round(base * (1 + percent.max / 100) * multiplier) / multiplier,
  };
}

function pushLine(
  lines: CalculatedItemPropertyLine[],
  key: ItemPropertyKey,
  label: string,
  value: string,
  augmented = false,
  source: CalculatedItemPropertyLine["source"] = "calculated",
) {
  lines.push({ key, label, value, augmented, source });
}

export function adjustedItemProperties(
  base: BaseItemSummary | undefined,
  quality: number,
  localMods: EditorModifier[],
  uniqueMods: UniqueItem["explicitMods"],
  customValues: CustomValueState,
): CalculatedItemPropertyLine[] {
  if (!base) return [];
  const properties = base.properties ?? {};
  const contributions = collectContributions(localMods, uniqueMods, customValues);
  const lines: CalculatedItemPropertyLine[] = [];
  const consumed = new Set<ItemPropertyKey>();

  const physicalBase = coerceDamageRange(properties.physicalDamage);
  if (physicalBase) {
    const value = calculatePhysicalDamageRange({
      base: physicalBase,
      flat: contributions.physicalFlat,
      percent: contributions.physicalPercent,
      quality,
    });
    const augmented =
      quality > 0 ||
      contributions.physicalFlat.min !== 0 ||
      contributions.physicalFlat.max !== 0 ||
      contributions.physicalPercent.min !== 0 ||
      contributions.physicalPercent.max !== 0;
    pushLine(lines, "physicalDamage", "Physical Damage", formatRange(value), augmented);
    consumed.add("physicalDamage");
  }

  for (const [element, label] of [
    ["fire", "Fire Damage"],
    ["cold", "Cold Damage"],
    ["lightning", "Lightning Damage"],
    ["chaos", "Chaos Damage"],
  ] as const) {
    const flat = contributions.elementalFlat[element];
    if (flat.min !== 0 || flat.max !== 0) {
      pushLine(lines, `${element}Damage`, label, formatRange(flat), true);
      consumed.add(`${element}Damage`);
    }
  }

  const critBase = coerceNumber(properties.criticalHitChance);
  if (critBase !== null) {
    const scaled = calculatePercentScaledValue({
      base: critBase + contributions.criticalChanceFlat.min,
      percent: contributions.criticalChancePercent,
      decimals: 2,
    });
    const maxScaled = calculatePercentScaledValue({
      base: critBase + contributions.criticalChanceFlat.max,
      percent: { min: contributions.criticalChancePercent.max, max: contributions.criticalChancePercent.max },
      decimals: 2,
    });
    const min = scaled.min;
    const max = maxScaled.max;
    const value = min === max ? formatPercent(min) : `${formatPercent(min)} - ${formatPercent(max)}`;
    const augmented =
      contributions.criticalChanceFlat.min !== 0 ||
      contributions.criticalChanceFlat.max !== 0 ||
      contributions.criticalChancePercent.min !== 0 ||
      contributions.criticalChancePercent.max !== 0;
    pushLine(lines, "criticalHitChance", "Critical Hit Chance", value, augmented);
    consumed.add("criticalHitChance");
  }

  const apsBase = coerceNumber(properties.attacksPerSecond);
  if (apsBase !== null) {
    const aps = calculatePercentScaledValue({
      base: apsBase,
      percent: contributions.attackSpeedPercent,
      decimals: 2,
    });
    const value = aps.min === aps.max ? formatDecimal(aps.min, 2) : `${formatDecimal(aps.min, 2)} - ${formatDecimal(aps.max, 2)}`;
    const augmented = contributions.attackSpeedPercent.min !== 0 || contributions.attackSpeedPercent.max !== 0;
    pushLine(lines, "attacksPerSecond", "Attacks per Second", value, augmented);
    consumed.add("attacksPerSecond");
  }

  const spiritBase = coerceNumber(properties.spirit);
  if (spiritBase !== null) {
    const min = spiritBase + contributions.spiritFlat.min;
    const max = spiritBase + contributions.spiritFlat.max;
    const value = min === max ? formatNumber(min) : `${formatNumber(min)} - ${formatNumber(max)}`;
    pushLine(lines, "spirit", "Spirit", value, contributions.spiritFlat.min !== 0 || contributions.spiritFlat.max !== 0);
    consumed.add("spirit");
  }

  const blockBase = parseBlockChance(properties.block_chance ?? properties.blockChance);
  if (blockBase !== null) {
    const flatMinBase = blockBase + contributions.blockChanceFlat.min;
    const flatMaxBase = blockBase + contributions.blockChanceFlat.max;
    const min = flatMinBase * (1 + contributions.blockChancePercent.min / 100);
    const max = flatMaxBase * (1 + contributions.blockChancePercent.max / 100);
    const value = Math.round(min * 100) / 100 === Math.round(max * 100) / 100
      ? formatPercent(Math.round(min * 100) / 100)
      : `${formatPercent(Math.round(min * 100) / 100)} - ${formatPercent(Math.round(max * 100) / 100)}`;
    const augmented =
      contributions.blockChanceFlat.min !== 0 ||
      contributions.blockChanceFlat.max !== 0 ||
      contributions.blockChancePercent.min !== 0 ||
      contributions.blockChancePercent.max !== 0;
    pushLine(lines, "blockChance", "Block chance", value, augmented);
    consumed.add("blockChance");
  }

  for (const line of base.propertyLines ?? []) {
    if (/^(Armou?r|Evasion(?: Rating)?|Energy Shield):/i.test(line)) continue;
    const key = propertyKeyFromLine(line);
    if (consumed.has(key)) continue;
    pushLine(lines, key, line.split(":")[0]?.trim() || displayKey(String(key)), line.includes(":") ? line.split(":").slice(1).join(":").trim() : "", false, "base");
    consumed.add(key);
  }

  return lines;
}
