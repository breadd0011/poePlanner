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

type SourceLabelMap = Record<string, string>;

export type DefenceKey = "armour" | "evasion" | "energyShield";

export type DefenceRange = {
  key: DefenceKey;
  label: string;
  min: number;
  max: number;
  augmented: boolean;
  breakdown: DefenceBreakdown;
};

export type NumericRange = { min: number; max: number };

export type ContributionSource =
  | "explicit"
  | "unique"
  | "corruption"
  | "socket"
  | "implicit";

export type LocalDefenceKind = "flat" | "increased";

export type DefenceContributionEntry = {
  source: ContributionSource;
  sourceLabel: string;
  kind: LocalDefenceKind;
  text: string;
  min: number;
  max: number;
};

export type DefenceContributionBucket = {
  flat: NumericRange;
  percent: NumericRange;
  entries: DefenceContributionEntry[];
};

export type DefenceContributions = Record<DefenceKey, DefenceContributionBucket>;

export type DefenceBreakdown = {
  base: number;
  flat: NumericRange;
  percent: NumericRange;
  quality: number;
  beforeQuality: NumericRange;
  entries: DefenceContributionEntry[];
  formula: string;
};

function emptyDefenceContributions(): DefenceContributions {
  return {
    armour: {
      flat: { min: 0, max: 0 },
      percent: { min: 0, max: 0 },
      entries: [],
    },
    evasion: {
      flat: { min: 0, max: 0 },
      percent: { min: 0, max: 0 },
      entries: [],
    },
    energyShield: {
      flat: { min: 0, max: 0 },
      percent: { min: 0, max: 0 },
      entries: [],
    },
  };
}

function normalizeDefenceKey(key: string): DefenceKey | null {
  const normalized = key.toLowerCase().replace(/[\s_-]+/g, "");
  if (normalized === "armour" || normalized === "armor") return "armour";
  if (normalized === "evasion" || normalized === "evasionrating")
    return "evasion";
  if (normalized === "energyshield") return "energyShield";
  return null;
}

export function baseDefenceValue(
  base: Pick<BaseItemSummary, "defences">,
  key: DefenceKey,
): number {
  for (const [rawKey, value] of Object.entries(base.defences)) {
    if (normalizeDefenceKey(rawKey) === key) return value;
  }
  return 0;
}

export function inferSubtypeFromBaseItem(
  base: Pick<BaseItemSummary, "defences"> | null | undefined,
  itemClass: string,
): string {
  if (!base) return "base";
  if (!["Shields", "Body Armours"].includes(itemClass)) return "base";
  const hasArmour = baseDefenceValue(base, "armour") > 0;
  const hasEvasion = baseDefenceValue(base, "evasion") > 0;
  const hasEnergyShield = baseDefenceValue(base, "energyShield") > 0;

  if (hasArmour && hasEvasion) return "str_dex";
  if (hasArmour && hasEnergyShield) return "str_int";
  if (hasEvasion && hasEnergyShield) return "dex_int";
  if (hasArmour) return "str";
  if (hasEvasion) return "dex";
  if (hasEnergyShield) return "int";
  return "base";
}

function addRange(target: NumericRange, range: NumericRange) {
  target.min += range.min;
  target.max += range.max;
}

export function rangeDebugText(range: NumericRange): string {
  return range.min === range.max
    ? formatNumber(range.min)
    : `${formatNumber(range.min)} - ${formatNumber(range.max)}`;
}

function customRangeForValue(
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

function fixedNumberRangeFromText(text: string): NumericRange | null {
  const match = text.match(/[+\-]?(\d+(?:\.\d+)?)/);
  if (!match) return null;
  const parsed = Number(match[0]);
  if (!Number.isFinite(parsed)) return null;
  return { min: parsed, max: parsed };
}

function firstModValueRange(
  mod: EditorModifier,
  customValues: CustomValueState,
): NumericRange | null {
  const values = getEditableValues(mod);
  if (values.length) {
    return customRangeForValue(
      values[0],
      customValues[mod.id]?.[values[0].index],
    );
  }
  return fixedNumberRangeFromText(mod.displayRangeText ?? mod.text);
}

function firstUniqueModValueRange(
  mod: UniqueItem["explicitMods"][number],
  customValues: CustomValueState,
): NumericRange | null {
  const values = parseInlineRanges(mod.text);
  if (values.length) {
    return customRangeForValue(
      values[0],
      customValues[mod.id]?.[values[0].index],
    );
  }
  return fixedNumberRangeFromText(mod.text);
}

function defenceTargetsFromText(
  text: string,
  base: BaseItemSummary,
): DefenceKey[] {
  const lower = text.toLowerCase();
  const targets: DefenceKey[] = [];
  if (/armou?r/.test(lower)) targets.push("armour");
  if (/evasion(?: rating)?/.test(lower)) targets.push("evasion");
  if (/energy shield/.test(lower)) targets.push("energyShield");

  // PoE2DB sometimes exposes generic essence text like "Armour, Evasion or Energy Shield".
  // On an actual item this resolves to the defence stat(s) the selected base can have.
  if (lower.includes(" or ")) {
    return targets.filter((key) => baseDefenceValue(base, key) > 0);
  }
  return targets;
}

function isLocalDefenceIncrease(text: string): boolean {
  const lower = text.toLowerCase();
  if (!/%\s+increased/.test(lower)) return false;
  if (!/(armou?r|evasion(?: rating)?|energy shield)/.test(lower)) return false;

  // These mention defence words but are not local item defence scaling.
  if (lower.includes("also applies")) return false;
  if (lower.startsWith("break ")) return false;
  if (lower.includes("deflection rating equal to")) return false;
  if (lower.includes("recharge")) return false;
  return true;
}

function isLocalFlatDefence(text: string): boolean {
  const lower = text.toLowerCase();
  if (!/(?:^|\s|\+)#?\(?[+\-]?\d*|#/.test(lower)) return false;
  if (!/\bto\b/.test(lower)) return false;
  if (
    !/(armou?r|evasion(?: rating)?|maximum energy shield|energy shield)/.test(
      lower,
    )
  )
    return false;

  if (lower.includes("maximum life")) return false;
  if (lower.includes("maximum mana")) return false;
  if (lower.includes("also applies")) return false;
  if (lower.includes("deflection rating")) return false;
  return !/%\s+increased/.test(lower);
}

export function editorContributionSource(mod: EditorModifier): ContributionSource {
  if (["augment", "bonded"].includes(mod.sourceMechanic)) return "socket";
  if (mod.sourceMechanic === "corrupted") return "corruption";
  return "explicit";
}

export function editorContributionSourceLabel(
  mod: EditorModifier,
  sourceLabels: SourceLabelMap,
): string {
  if (["augment", "bonded"].includes(mod.sourceMechanic)) return "Socket";
  if (mod.sourceMechanic === "corrupted") return "Corruption";
  return (
    (sourceLabels[mod.sourceMechanic] ?? displayKey(mod.sourceMechanic)) ||
    "Explicit"
  );
}

function addContributionEntry(
  bucket: DefenceContributionBucket,
  entry: DefenceContributionEntry,
) {
  bucket.entries.push(entry);
  addRange(entry.kind === "flat" ? bucket.flat : bucket.percent, {
    min: entry.min,
    max: entry.max,
  });
}

function applyLocalDefenceContribution(
  contributions: DefenceContributions,
  base: BaseItemSummary,
  text: string,
  value: NumericRange | null,
  source: ContributionSource,
  sourceLabel: string,
) {
  const targets = defenceTargetsFromText(text, base);
  if (!targets.length || !value) return;

  const kind: LocalDefenceKind | null = isLocalDefenceIncrease(text)
    ? "increased"
    : isLocalFlatDefence(text)
      ? "flat"
      : null;
  if (!kind) return;

  for (const key of targets) {
    addContributionEntry(contributions[key], {
      source,
      sourceLabel,
      kind,
      text,
      min: value.min,
      max: value.max,
    });
  }
}

function collectLocalDefenceContributions(
  base: BaseItemSummary,
  mods: EditorModifier[],
  uniqueMods: UniqueItem["explicitMods"],
  customValues: CustomValueState,
  sourceLabels: SourceLabelMap,
): DefenceContributions {
  const contributions = emptyDefenceContributions();
  for (const mod of mods) {
    applyLocalDefenceContribution(
      contributions,
      base,
      renderModifierText(mod, customValues),
      firstModValueRange(mod, customValues),
      editorContributionSource(mod),
      editorContributionSourceLabel(mod, sourceLabels),
    );
  }
  for (const mod of uniqueMods) {
    applyLocalDefenceContribution(
      contributions,
      base,
      renderUniqueModText(mod, customValues),
      firstUniqueModValueRange(mod, customValues),
      "unique",
      "Built-in explicit",
    );
  }
  return contributions;
}

export function calculateDefenceRange({
  base,
  flat,
  percent,
  quality,
}: {
  base: number;
  flat: NumericRange;
  percent: NumericRange;
  quality: number;
}): NumericRange {
  const safeQuality = Math.max(0, Math.min(30, quality));
  const qualityMultiplier = 1 + safeQuality / 100;
  const minBeforeQuality = (base + flat.min) * (1 + percent.min / 100);
  const maxBeforeQuality = (base + flat.max) * (1 + percent.max / 100);
  return {
    min: Math.floor(minBeforeQuality * qualityMultiplier),
    max: Math.floor(maxBeforeQuality * qualityMultiplier),
  };
}

export function formatDefenceValue(min: number, max: number): string {
  const safeMin = Math.floor(min);
  const safeMax = Math.floor(max);
  return safeMin === safeMax ? String(safeMin) : `${safeMin} - ${safeMax}`;
}

function breakdownFormula(
  base: number,
  flat: NumericRange,
  percent: NumericRange,
  quality: number,
): string {
  const flatText = rangeDebugText(flat);
  const percentText = rangeDebugText(percent);
  return `floor((${formatNumber(base)} + ${flatText}) × (1 + ${percentText} / 100) × (1 + ${quality} / 100))`;
}

export function adjustedDefences(
  base: BaseItemSummary | undefined,
  quality: number,
  localMods: EditorModifier[],
  uniqueMods: UniqueItem["explicitMods"],
  customValues: CustomValueState,
  sourceLabels: SourceLabelMap,
): DefenceRange[] {
  if (!base) return [];
  const safeQuality = Math.max(0, Math.min(30, quality));
  const qualityMultiplier = 1 + safeQuality / 100;
  const contributions = collectLocalDefenceContributions(
    base,
    localMods,
    uniqueMods,
    customValues,
    sourceLabels,
  );

  return Object.entries(base.defences).map(([rawKey, baseValue]) => {
    const key = normalizeDefenceKey(rawKey);
    if (!key) {
      return {
        key: rawKey as DefenceKey,
        label: displayKey(rawKey),
        min: Math.floor(baseValue * qualityMultiplier),
        max: Math.floor(baseValue * qualityMultiplier),
        augmented: safeQuality > 0,
        breakdown: {
          base: baseValue,
          flat: { min: 0, max: 0 },
          percent: { min: 0, max: 0 },
          quality: safeQuality,
          beforeQuality: { min: baseValue, max: baseValue },
          entries: [],
          formula: breakdownFormula(
            baseValue,
            { min: 0, max: 0 },
            { min: 0, max: 0 },
            safeQuality,
          ),
        },
      };
    }
    const local = contributions[key];
    const minBeforeQuality =
      (baseValue + local.flat.min) * (1 + local.percent.min / 100);
    const maxBeforeQuality =
      (baseValue + local.flat.max) * (1 + local.percent.max / 100);
    const adjustedRange = calculateDefenceRange({
      base: baseValue,
      flat: local.flat,
      percent: local.percent,
      quality: safeQuality,
    });
    return {
      key,
      label: displayKey(rawKey),
      min: adjustedRange.min,
      max: adjustedRange.max,
      augmented:
        safeQuality > 0 ||
        local.flat.min !== 0 ||
        local.flat.max !== 0 ||
        local.percent.min !== 0 ||
        local.percent.max !== 0,
      breakdown: {
        base: baseValue,
        flat: { ...local.flat },
        percent: { ...local.percent },
        quality: safeQuality,
        beforeQuality: { min: minBeforeQuality, max: maxBeforeQuality },
        entries: local.entries,
        formula: breakdownFormula(
          baseValue,
          local.flat,
          local.percent,
          safeQuality,
        ),
      },
    };
  });
}
