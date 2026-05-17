import { useEffect, useMemo, useState } from "react";
import type { EditorModifier, EditorModifierPool } from "../../../types";
import {
  type PickerKind,
  pickerSources,
} from "../components/item-editor/editorTypes";
import { type AugmentLookupIndex, socketModifierAppliesToItemClass } from "../domain/augmentEffects";

function countBySource(
  pools: EditorModifierPool[],
): Map<EditorModifierPool["sourceMechanic"], number> {
  const counts = new Map<EditorModifierPool["sourceMechanic"], number>();
  for (const pool of pools)
    counts.set(
      pool.sourceMechanic,
      (counts.get(pool.sourceMechanic) ?? 0) + pool.mods.length,
    );
  return counts;
}

function modifierSearchText(mod: EditorModifier): string {
  if (mod.searchText) return mod.searchText.toLowerCase();
  return [
    mod.text,
    mod.displayRangeText ?? "",
    mod.pickerLabel ?? "",
    mod.runeName ?? "",
    mod.augmentName ?? "",
    mod.augmentCategory ?? "",
    mod.augmentSourceUrl ?? "",
    mod.socketStatText ?? "",
    mod.sourceGroup,
    mod.sourceMechanic,
    mod.family ?? "",
    mod.tags.join(" "),
    mod.keywords.join(" "),
  ]
    .join(" ")
    .toLowerCase();
}

export function useModifierPicker({
  subtypePools,
  sourceOrder,
  selectedItemClass,
  augmentIndex,
}: {
  subtypePools: EditorModifierPool[];
  sourceOrder: EditorModifierPool["sourceMechanic"][];
  selectedItemClass: string;
  augmentIndex: AugmentLookupIndex;
}) {
  const [pickerKind, setPickerKind] = useState<PickerKind>(null);
  const [pickerQuery, setPickerQuery] = useState("");
  const [pickerTag, setPickerTag] = useState("all");
  const [pickerSourcesState, setPickerSourcesState] = useState<
    EditorModifierPool["sourceMechanic"][]
  >(["normal"]);

  const allSubtypeMods = useMemo(
    () => subtypePools.flatMap((pool) => pool.mods),
    [subtypePools],
  );

  const sourceCounts = useMemo(
    () => countBySource(subtypePools),
    [subtypePools],
  );

  const pickerAllowedSources = useMemo(
    () => (pickerKind ? pickerSources(pickerKind) : []),
    [pickerKind],
  );

  const pickerAvailableSources = useMemo(
    () =>
      sourceOrder.filter(
        (source) =>
          pickerAllowedSources.includes(source) && sourceCounts.has(source),
      ),
    [pickerAllowedSources, sourceCounts, sourceOrder],
  );

  const activePickerSources = pickerSourcesState.filter((source) =>
    pickerAvailableSources.includes(source),
  );

  useEffect(() => {
    if (!pickerKind) return;
    const nextSources = pickerSources(pickerKind).filter((source) =>
      sourceCounts.has(source),
    );
    setPickerSourcesState(nextSources.length ? nextSources : []);
    setPickerQuery("");
    setPickerTag("all");
  }, [pickerKind, sourceCounts]);

  const pickerSourceMods = useMemo(() => {
    const active = activePickerSources.length
      ? activePickerSources
      : pickerAvailableSources;
    return subtypePools
      .filter((pool) => active.includes(pool.sourceMechanic))
      .flatMap((pool) => pool.mods);
  }, [activePickerSources, pickerAvailableSources, subtypePools]);

  const pickerTagOptions = useMemo(() => {
    const tags = new Set<string>();
    for (const mod of pickerSourceMods)
      for (const tag of mod.tags) tags.add(tag);
    return ["all", ...Array.from(tags).sort((a, b) => a.localeCompare(b))];
  }, [pickerSourceMods]);

  const visiblePickerMods = useMemo(() => {
    const normalizedQuery = pickerQuery.trim().toLowerCase();
    return pickerSourceMods.filter((mod) => {
      if (pickerKind === "socket" && !socketModifierAppliesToItemClass({ itemClass: selectedItemClass, mod, lookup: augmentIndex })) return false;
      if (pickerTag !== "all" && !mod.tags.includes(pickerTag)) return false;
      if (normalizedQuery && !modifierSearchText(mod).includes(normalizedQuery))
        return false;
      return true;
    });
  }, [augmentIndex, pickerKind, pickerQuery, pickerSourceMods, pickerTag, selectedItemClass]);

  function togglePickerSource(source: EditorModifierPool["sourceMechanic"]) {
    setPickerSourcesState((current) => {
      if (current.includes(source)) {
        const next = current.filter((candidate) => candidate !== source);
        return next.length ? next : current;
      }
      return [...current, source];
    });
  }

  function resetPicker() {
    setPickerKind(null);
    setPickerQuery("");
    setPickerTag("all");
    setPickerSourcesState(["normal"]);
  }

  return {
    activePickerSources,
    allSubtypeMods,
    pickerAvailableSources,
    pickerKind,
    pickerQuery,
    pickerTag,
    pickerTagOptions,
    resetPicker,
    setPickerKind,
    setPickerQuery,
    setPickerTag,
    sourceCounts,
    togglePickerSource,
    visiblePickerMods,
  };
}
