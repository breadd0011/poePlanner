import { useId, useMemo, useRef } from "react";
import type { FocusEvent, MouseEvent } from "react";
import type { EditorModifier, EditorModifierPool, PlannerAugment } from "../../../../types";
import { type AugmentLookupIndex, findAugmentForSocketModifier } from "../../domain/augmentEffects";
import {
  type CustomValueState,
  displayKey,
  renderModifierListLabel,
} from "../../domain/itemText";
import {
  PICKER_LABELS,
  pickerDescription,
  type PickerKind,
  type SourceLabelMap,
} from "./editorTypes";
import {
  augmentTooltipId,
  FloatingAugmentTooltip,
  useFloatingAugmentTooltip,
} from "./FloatingAugmentTooltip";
import { useModalFocusTrap } from "../../hooks/useModalFocusTrap";

function sourceButtonClass(active: boolean): string {
  return active ? "editor-pill editor-pill--active" : "editor-pill";
}

type ModifierPickerSection = {
  key: string;
  title: string | null;
  mods: EditorModifier[];
};

function socketAugmentName(mod: EditorModifier): string {
  return mod.augmentName ?? mod.runeName ?? mod.pickerLabel ?? mod.text;
}

function socketAugmentGroupKey(mod: EditorModifier): string {
  const configuredGroup = (mod.socketPickerGroup ?? mod.pickerGroup ?? "").trim().toLowerCase().replace(/[_\s]+/g, "-");
  if (["lesser-runes", "runes", "greater-runes", "soul-cores", "other-augments"].includes(configuredGroup)) return configuredGroup;

  const category = (mod.augmentCategory ?? "").toLowerCase();
  const name = socketAugmentName(mod).toLowerCase();
  if (category === "soul_core" || name.includes("soul core")) return "soul-cores";
  if (name.endsWith(" rune") || category === "rune_item" || category === "rune_like_augment") {
    if (name.startsWith("lesser ")) return "lesser-runes";
    if (name.startsWith("greater ")) return "greater-runes";
    return "runes";
  }
  return "other-augments";
}

const SOCKET_AUGMENT_GROUPS = [
  ["lesser-runes", "Lesser Runes"],
  ["runes", "Runes"],
  ["greater-runes", "Greater Runes"],
  ["soul-cores", "Soul Cores"],
  ["other-augments", "Other Socketable Augments"],
] as const;

function runeSortLabel(mod: EditorModifier): string {
  return (mod.sortLabel ?? socketAugmentName(mod).replace(/^(lesser|greater)\s+/i, "")).toLowerCase();
}

function buildModifierSections(
  kind: Exclude<PickerKind, null>,
  mods: EditorModifier[],
): ModifierPickerSection[] {
  if (kind !== "socket") return [{ key: "all", title: null, mods }];

  const groups = new Map<string, EditorModifier[]>();
  const otherMods: EditorModifier[] = [];
  for (const mod of mods) {
    if (mod.sourceMechanic === "augment") {
      const key = socketAugmentGroupKey(mod);
      const group = groups.get(key) ?? [];
      group.push(mod);
      groups.set(key, group);
    } else {
      otherMods.push(mod);
    }
  }

  const sections: ModifierPickerSection[] = [];
  for (const [key, title] of SOCKET_AUGMENT_GROUPS) {
    const group = groups.get(key);
    if (!group?.length) continue;
    sections.push({
      key,
      title,
      mods: [...group].sort((a, b) => {
        const nameCompare = runeSortLabel(a).localeCompare(runeSortLabel(b));
        if (nameCompare !== 0) return nameCompare;
        return socketAugmentName(a).localeCompare(socketAugmentName(b));
      }),
    });
  }

  if (otherMods.length) {
    sections.push({ key: "other", title: "Other socket options", mods: otherMods });
  }

  return sections;
}

export function ModifierPicker({
  kind,
  mods,
  availableSources,
  activeSources,
  sourceCounts,
  sourceLabels,
  selectedIds,
  customValues,
  augmentIndex,
  query,
  activeTag,
  tagOptions,
  onQueryChange,
  onTagChange,
  onToggleSource,
  onSelect,
  onClose,
}: {
  kind: Exclude<PickerKind, null>;
  mods: EditorModifier[];
  availableSources: EditorModifierPool["sourceMechanic"][];
  activeSources: EditorModifierPool["sourceMechanic"][];
  sourceCounts: Map<EditorModifierPool["sourceMechanic"], number>;
  sourceLabels: SourceLabelMap;
  selectedIds: string[];
  customValues: CustomValueState;
  augmentIndex: AugmentLookupIndex;
  query: string;
  activeTag: string;
  tagOptions: string[];
  onQueryChange: (value: string) => void;
  onTagChange: (value: string) => void;
  onToggleSource: (source: EditorModifierPool["sourceMechanic"]) => void;
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const floatingTooltip = useFloatingAugmentTooltip();
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const modifierSections = useMemo(
    () => buildModifierSections(kind, mods),
    [kind, mods],
  );

  useModalFocusTrap({ ref: dialogRef, onClose });

  function handleMouseEnter(
    event: MouseEvent<HTMLButtonElement>,
    augment: PlannerAugment | null,
    tooltipId: string | undefined,
  ) {
    floatingTooltip.show(augment, tooltipId, event.currentTarget);
  }

  function handleFocus(
    event: FocusEvent<HTMLButtonElement>,
    augment: PlannerAugment | null,
    tooltipId: string | undefined,
  ) {
    floatingTooltip.show(augment, tooltipId, event.currentTarget);
  }

  return (
    <div
      className="modifier-picker-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        aria-describedby={descriptionId}
        aria-labelledby={titleId}
        aria-modal="true"
        className="modifier-picker"
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="modifier-picker-header">
          <div>
            <strong id={titleId}>{PICKER_LABELS[kind]}</strong>
            <p id={descriptionId}>{pickerDescription(kind)}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close modifier picker">
            ×
          </button>
        </header>

        <div className="modifier-picker-controls">
          <label className="editor-field">
            <span>Search</span>
            <input
              autoFocus
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="life, resistance, augment..."
            />
          </label>
          <label className="editor-field">
            <span>Tag</span>
            <select
              value={activeTag}
              onChange={(event) => onTagChange(event.target.value)}
            >
              {tagOptions.map((tag) => (
                <option key={tag} value={tag}>
                  {tag === "all" ? "All tags" : tag}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="source-pill-row modifier-picker-sources">
          {availableSources.map((source) => (
            <button
              className={sourceButtonClass(activeSources.includes(source))}
              key={source}
              onClick={() => onToggleSource(source)}
              type="button"
            >
              <span>{sourceLabels[source] ?? displayKey(source)}</span>
              <small>{sourceCounts.get(source) ?? 0}</small>
            </button>
          ))}
        </div>

        <div className="modifier-picker-list" onScroll={floatingTooltip.hide}>
          {mods.length ? (
            modifierSections.map((section) => (
              <section className="modifier-picker-section" key={section.key}>
                {section.title ? (
                  <div className="modifier-picker-section-title">
                    <span>{section.title}</span>
                    <small>{section.mods.length}</small>
                  </div>
                ) : null}
                <div className="modifier-picker-section-list">
                  {section.mods.map((mod) => {
                    const augment = findAugmentForSocketModifier(mod, augmentIndex);
                    const tooltipId = augment ? augmentTooltipId(mod.id) : undefined;
                    return (
                      <div className="picker-mod-row-shell" key={mod.id}>
                        <button
                          aria-describedby={tooltipId}
                          className={
                            selectedIds.includes(mod.id)
                              ? "picker-mod-row picker-mod-row--selected"
                              : "picker-mod-row"
                          }
                          type="button"
                          onClick={() => onSelect(mod.id)}
                          onMouseEnter={(event) => handleMouseEnter(event, augment, tooltipId)}
                          onMouseLeave={floatingTooltip.hide}
                          onFocus={(event) => handleFocus(event, augment, tooltipId)}
                          onBlur={floatingTooltip.hide}
                        >
                          <strong>{renderModifierListLabel(mod, customValues)}</strong>
                          <span>
                            {sourceLabels[mod.sourceMechanic] ??
                              displayKey(mod.sourceMechanic)}
                            {mod.affixType ? ` · ${mod.affixType}` : ""}
                            {mod.tags.length ? ` · ${mod.tags.join(" · ")}` : ""}
                          </span>
                        </button>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))
          ) : (
            <p className="muted">No modifiers match the current filters.</p>
          )}
        </div>
      </div>

      <FloatingAugmentTooltip state={floatingTooltip.state} />
    </div>
  );
}
