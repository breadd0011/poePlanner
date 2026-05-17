import type { EditableValueRange, EditorModifier, UniqueItem } from "../../../../types";
import {
  type CustomValueState,
  formatNumber,
  getEditableValues,
  normalizeRangeDashes,
  parseInlineRanges,
  renderModifierListLabel,
  renderUniqueModText,
} from "../../domain/itemText";

function inputBoundsForRange(range: EditableValueRange) {
  const min = range.min;
  const max = range.max;
  const prefixIsNegative = range.valuePrefix === "-";
  const normalizedMin = min === null ? undefined : prefixIsNegative ? Math.abs(min) : min;
  const normalizedMax = max === null ? undefined : prefixIsNegative ? Math.abs(max) : max;
  return {
    min: normalizedMin === undefined || normalizedMax === undefined
      ? normalizedMin
      : Math.min(normalizedMin, normalizedMax),
    max: normalizedMin === undefined || normalizedMax === undefined
      ? normalizedMax
      : Math.max(normalizedMin, normalizedMax),
  };
}

function placeholderForRange(range: EditableValueRange): string {
  if (range.min !== null && range.max !== null) {
    const min = formatNumber(Math.abs(range.min));
    const max = formatNumber(Math.abs(range.max));
    return min === max ? min : `${min} - ${max}`;
  }
  return "value";
}

function titleForRange(range: EditableValueRange): string {
  if (range.min !== null && range.max !== null) {
    const prefix = range.valuePrefix ?? "";
    return `Allowed: ${prefix}${formatNumber(range.min)} to ${prefix}${formatNumber(range.max)}`;
  }
  return "Custom stat value";
}

function sanitizeRangeInput(value: string, range: EditableValueRange): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const bounds = inputBoundsForRange(range);
  const prefixIsNegative = range.valuePrefix === "-";
  const parsed = Number(trimmed.replace(",", "."));
  if (!Number.isFinite(parsed)) return "";

  let next = prefixIsNegative ? Math.abs(parsed) : parsed;
  if (bounds.min !== undefined) next = Math.max(bounds.min, next);
  if (bounds.max !== undefined) next = Math.min(bounds.max, next);
  return formatNumber(next);
}

function draftRangeInput(value: string, range: EditableValueRange): string {
  const normalized = value.replace(",", ".");
  if (!normalized.trim()) return "";
  if (!/^-?\d*(?:\.\d*)?$/.test(normalized)) return "";

  const prefixIsNegative = range.valuePrefix === "-";
  return prefixIsNegative ? normalized.replace("-", "") : normalized;
}

function replaceFirstRangeText(
  output: Array<string | EditableValueRange>,
  range: EditableValueRange,
): Array<string | EditableValueRange> {
  const rangeText = range.rangeText ? normalizeRangeDashes(range.rangeText) : "";
  const rangeRegex = /([+\-]?)(\(?\s*-?\d+(?:\.\d+)?\s*[—–-]\s*-?\d+(?:\.\d+)?\s*\)?)/;

  for (const [index, part] of output.entries()) {
    if (typeof part !== "string") continue;
    const normalizedPart = normalizeRangeDashes(part);
    const matchIndex = rangeText ? normalizedPart.indexOf(rangeText) : -1;
    if (matchIndex >= 0) {
      return [
        ...output.slice(0, index),
        normalizedPart.slice(0, matchIndex),
        range,
        normalizedPart.slice(matchIndex + rangeText.length),
        ...output.slice(index + 1),
      ];
    }

    const match = part.match(rangeRegex);
    if (match?.index !== undefined) {
      return [
        ...output.slice(0, index),
        part.slice(0, match.index),
        range,
        part.slice(match.index + match[0].length),
        ...output.slice(index + 1),
      ];
    }
  }

  return [...output, " ", range];
}

function tokenizedParts(text: string, ranges: EditableValueRange[]) {
  const normalizedText = normalizeRangeDashes(text);
  if (normalizedText.includes("#")) {
    const textParts = normalizedText.split("#");
    const parts: Array<string | EditableValueRange> = [];
    textParts.forEach((part, index) => {
      parts.push(part);
      if (index < ranges.length) parts.push(ranges[index]);
    });
    return parts;
  }

  return ranges.reduce<Array<string | EditableValueRange>>(
    (parts, range) => replaceFirstRangeText(parts, range),
    [normalizedText],
  );
}

function EditableStatText({
  modId,
  text,
  ranges,
  customValues,
  onValueChange,
}: {
  modId: string;
  text: string;
  ranges: EditableValueRange[];
  customValues: CustomValueState;
  onValueChange: (modId: string, index: number, value: string) => void;
}) {
  if (!ranges.length) return <>{normalizeRangeDashes(text)}</>;

  const parts = tokenizedParts(text, ranges);
  return (
    <>
      {parts.map((part, index) => {
        if (typeof part === "string") return <span key={`text:${index}`}>{part}</span>;

        const rawValue = customValues[modId]?.[part.index] ?? "";
        const prefix = part.valuePrefix ?? "";
        const suffix = part.valueSuffix ?? "";
        const placeholder = placeholderForRange(part);
        const inputWidthCh = Math.min(Math.max(placeholder.length + 2, 4), 11);
        return (
          <span className="planner-editable-number" key={`value:${part.index}:${index}`}>
            {prefix ? <span>{prefix}</span> : null}
            <input
              type="text"
              inputMode="decimal"
              style={{ width: `${inputWidthCh}ch` }}
              placeholder={placeholder}
              title={titleForRange(part)}
              value={rawValue}
              onChange={(event) => {
                const next = draftRangeInput(event.target.value, part);
                if (next || !event.target.value.trim()) {
                  onValueChange(modId, part.index, next);
                }
              }}
              onBlur={(event) =>
                onValueChange(
                  modId,
                  part.index,
                  sanitizeRangeInput(event.target.value, part),
                )
              }
            />
            {suffix ? <span>{suffix}</span> : null}
          </span>
        );
      })}
    </>
  );
}

function UniqueStatLine({
  mod,
  customValues,
  onValueChange,
}: {
  mod: UniqueItem["explicitMods"][number];
  customValues: CustomValueState;
  onValueChange: (modId: string, index: number, value: string) => void;
}) {
  const ranges = parseInlineRanges(mod.text);
  return (
    <li className="planner-stat-line planner-stat-line--built-in planner-stat-line--poe2db">
      <div className="planner-stat-content planner-stat-content--poe2db">
        <div>
          {ranges.length ? (
            <EditableStatText
              modId={mod.id}
              text={mod.text}
              ranges={ranges}
              customValues={customValues}
              onValueChange={onValueChange}
            />
          ) : (
            renderUniqueModText(mod, customValues)
          )}
        </div>
      </div>
    </li>
  );
}

function StatLine({
  mod,
  customValues,
  onRemove,
  onValueChange,
}: {
  mod: EditorModifier;
  customValues: CustomValueState;
  onRemove: (id: string) => void;
  onValueChange: (modId: string, index: number, value: string) => void;
}) {
  const ranges = getEditableValues(mod);
  const text = mod.sourceMechanic === "augment" && mod.pickerLabel
    ? mod.pickerLabel
    : mod.textTemplate ?? mod.displayRangeText ?? mod.text;
  return (
    <li className="planner-stat-line planner-stat-line--poe2db planner-stat-line--removable">
      <div className="planner-stat-content planner-stat-content--poe2db">
        <div>
          {ranges.length ? (
            <EditableStatText
              modId={mod.id}
              text={text}
              ranges={ranges}
              customValues={customValues}
              onValueChange={onValueChange}
            />
          ) : (
            renderModifierListLabel(mod, customValues)
          )}
        </div>
      </div>
      <button
        className="planner-stat-remove-button planner-stat-remove-button--inline"
        title="Remove stat"
        type="button"
        onClick={() => onRemove(mod.id)}
        aria-label="Remove stat"
      >
        <svg aria-hidden="true" viewBox="0 0 12 12" focusable="false">
          <path d="M2 2l8 8M10 2l-8 8" />
        </svg>
      </button>
    </li>
  );
}

function AddRow({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <li className="planner-stat-line planner-stat-line--empty planner-stat-line--add planner-stat-line--poe2db">
      <button
        className="planner-stat-content planner-stat-content--poe2db planner-stat-add-button"
        type="button"
        onClick={onClick}
      >
        {`<${label}>`}
      </button>
    </li>
  );
}

export function StatCategory({
  title,
  mods,
  uniqueMods = [],
  customValues,
  addLabel,
  onAdd,
  onRemove,
  onValueChange,
}: {
  title: string;
  mods: EditorModifier[];
  uniqueMods?: UniqueItem["explicitMods"];
  customValues: CustomValueState;
  addLabel: string;
  onAdd: () => void;
  onRemove: (id: string) => void;
  onValueChange: (modId: string, index: number, value: string) => void;
}) {
  return (
    <section className="planner-stat-category">
      <h3>{title}</h3>
      <ul className="planner-stat-list planner-stat-list--poe2db">
        {uniqueMods.map((mod) => (
          <UniqueStatLine
            key={mod.id}
            mod={mod}
            customValues={customValues}
            onValueChange={onValueChange}
          />
        ))}
        {mods.map((mod, index) => (
          <StatLine
            key={`${mod.id}:${index}`}
            mod={mod}
            customValues={customValues}
            onRemove={onRemove}
            onValueChange={onValueChange}
          />
        ))}
        <AddRow label={addLabel} onClick={onAdd} />
      </ul>
    </section>
  );
}

export function SocketCategory({
  mods,
  customValues,
  capacity,
  onAdd,
  onRemove,
  onValueChange,
}: {
  mods: EditorModifier[];
  customValues: CustomValueState;
  capacity: number;
  onAdd: () => void;
  onRemove: (id: string) => void;
  onValueChange: (modId: string, index: number, value: string) => void;
}) {
  const emptySlots = Math.max(0, capacity - mods.length);
  return (
    <section className="planner-stat-category">
      <h3>
        {capacity} {capacity === 1 ? "Socket" : "Sockets"}
      </h3>
      <ul className="planner-stat-list planner-stat-list--poe2db">
        {mods.map((mod, index) => (
          <StatLine
            key={`${mod.id}:${index}`}
            mod={mod}
            customValues={customValues}
            onRemove={onRemove}
            onValueChange={onValueChange}
          />
        ))}
        {Array.from({ length: emptySlots }).map((_, index) => (
          <li
            className="planner-stat-line planner-stat-line--empty planner-stat-line--add planner-stat-line--poe2db"
            key={`empty:${index}`}
          >
            <button
              className="planner-stat-content planner-stat-content--poe2db planner-stat-add-button socket-empty-row"
              type="button"
              onClick={onAdd}
            >
              <span className="socket-dot" />
              <span>Empty Socket</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
