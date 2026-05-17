import type { EditableValueRange, EditorModifier, UniqueItem } from "../../../types";

export type CustomValueState = Record<string, Record<number, string>>;

export function displayKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(/[_\s]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}


export function normalizeRangeDashes(text: string): string {
  return text
    .replace(/\s*[—–]\s*/g, " - ")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatNumber(value: number): string {
  return Number.isInteger(value)
    ? String(value)
    : String(Number(value.toFixed(4)))
        .replace(/0+$/, "")
        .replace(/\.$/, "");
}

export function rangeToDisplay(range: EditableValueRange): string {
  if (range.rangeText) return normalizeRangeDashes(range.rangeText);
  if (range.min !== null && range.max !== null) {
    if (range.min === range.max)
      return `${range.valuePrefix ?? ""}${formatNumber(range.min)}${range.valueSuffix ?? ""}`;
    return `${range.valuePrefix ?? ""}(${formatNumber(range.min)} - ${formatNumber(range.max)})${range.valueSuffix ?? ""}`;
  }
  return "#";
}

export function parseInlineRanges(text: string): EditableValueRange[] {
  const values: EditableValueRange[] = [];
  const rangePattern =
    /([+\-]?)(\(?\s*(-?\d+(?:\.\d+)?)\s*[—–-]\s*(-?\d+(?:\.\d+)?)\s*\)?)/g;
  let match: RegExpExecArray | null;
  while ((match = rangePattern.exec(text)) !== null) {
    const sign = match[1] ?? "";
    const min = Number(match[3]);
    const max = Number(match[4]);
    if (!Number.isFinite(min) || !Number.isFinite(max)) continue;
    values.push({
      index: values.length,
      min: Math.min(min, max),
      max: Math.max(min, max),
      value: null,
      rangeText: match[0],
      valuePrefix: sign,
      valueSuffix: "",
    });
  }
  return values;
}

function decimalFixValues(
  mod: EditorModifier,
  values: EditableValueRange[],
): EditableValueRange[] {
  const text =
    `${mod.family ?? ""} ${mod.generationGroup ?? ""} ${mod.text}`.toLowerCase();
  if (
    text.includes("rebirthrune") ||
    text.includes("regenerate #% of maximum life per second")
  ) {
    return [
      {
        index: 0,
        min: 0.25,
        max: 0.35,
        value: null,
        rangeText: "(0.25 - 0.35)",
        valuePrefix: "",
        valueSuffix: "",
      },
    ];
  }
  return values;
}

export function getEditableValues(mod: EditorModifier): EditableValueRange[] {
  const raw = mod.editableValues ?? [];
  const nonZeroRaw = raw.filter(
    (range) => !(range.min === 0 && range.max === 0 && /%/.test(mod.text)),
  );
  const parsed = nonZeroRaw.length
    ? nonZeroRaw
    : parseInlineRanges(mod.displayRangeText ?? mod.text);
  return decimalFixValues(mod, parsed);
}

export function formatCustomValue(
  range: EditableValueRange,
  raw: string | undefined,
): string {
  const normalized = raw?.trim();
  if (!normalized) return rangeToDisplay(range);
  return `${range.valuePrefix ?? ""}${normalized}${range.valueSuffix ?? ""}`;
}

export function replaceFirstRange(
  output: string,
  range: EditableValueRange,
  replacement: string,
): string {
  if (range.rangeText && output.includes(range.rangeText))
    return output.replace(range.rangeText, replacement);
  const normalized = normalizeRangeDashes(output);
  const normalizedRange = normalizeRangeDashes(range.rangeText ?? "");
  if (normalizedRange && normalized.includes(normalizedRange))
    return normalized.replace(normalizedRange, replacement);
  return output.replace(
    /([+\-]?)(\(?\s*-?\d+(?:\.\d+)?\s*[—–-]\s*-?\d+(?:\.\d+)?\s*\)?)/,
    replacement,
  );
}

export function renderModifierText(
  mod: EditorModifier,
  customValues: CustomValueState,
): string {
  const values = getEditableValues(mod);
  if (!values.length)
    return normalizeRangeDashes(mod.displayRangeText ?? mod.text);

  const overrides = customValues[mod.id] ?? {};
  const hasAnyOverride = values.some(
    (range) => String(overrides[range.index] ?? "").trim() !== "",
  );
  if (!hasAnyOverride) {
    if (mod.displayRangeText) return normalizeRangeDashes(mod.displayRangeText);
    let rangeOutput = mod.text;
    for (const range of values) {
      rangeOutput = rangeOutput.includes("#")
        ? rangeOutput.replace("#", rangeToDisplay(range))
        : replaceFirstRange(rangeOutput, range, rangeToDisplay(range));
    }
    return normalizeRangeDashes(rangeOutput);
  }

  let output = mod.textTemplate ?? mod.text;
  for (const range of values) {
    const replacement = formatCustomValue(range, overrides[range.index]);
    output = output.includes("#")
      ? output.replace("#", replacement)
      : replaceFirstRange(output, range, replacement);
  }
  return normalizeRangeDashes(output);
}

export function renderModifierListLabel(
  mod: EditorModifier,
  customValues: CustomValueState,
): string {
  if (mod.sourceMechanic === "augment" && mod.pickerLabel) {
    return normalizeRangeDashes(mod.pickerLabel);
  }
  return renderModifierText(mod, customValues);
}


export function renderUniqueModText(
  mod: UniqueItem["explicitMods"][number],
  customValues: CustomValueState,
): string {
  const values = parseInlineRanges(mod.text);
  if (!values.length) return normalizeRangeDashes(mod.text);
  const overrides = customValues[mod.id] ?? {};
  let output = mod.text;
  for (const range of values) {
    const replacement = formatCustomValue(range, overrides[range.index]);
    output = replaceFirstRange(output, range, replacement);
  }
  return normalizeRangeDashes(output);
}


