import { useEffect, useMemo, useState } from "react";
import type { EditorModifier } from "../../../types";
import type { EquippedItemDraft } from "../domain/equipment";
import {
  corruptedAfterModifierSelection,
  corruptedAfterSocketCountChange,
  getSelectedBuckets,
  legalSocketCountForCorruptionState,
  sameOrderedIds,
  sanitizeSelectionIdsForCorruptionState,
  socketCountAfterCorruptedChange,
  trimSocketSelectionIds,
} from "../domain/itemSockets";
import type { CustomValueState } from "../domain/itemText";

export function useItemModifierState({
  allSubtypeMods,
  resetPicker,
  closePicker,
  maxSocketCount = 6,
}: {
  allSubtypeMods: EditorModifier[];
  resetPicker: () => void;
  closePicker: () => void;
  maxSocketCount?: number;
}) {
  const [isCorrupted, setIsCorrupted] = useState(false);
  const [socketCount, setSocketCount] = useState(2);
  const normalizedMaxSocketCount = Math.max(0, Math.floor(Number.isFinite(maxSocketCount) ? maxSocketCount : 0));
  const [isSanctified, setIsSanctified] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [customValues, setCustomValues] = useState<CustomValueState>({});

  const selectedMods = useMemo(
    () =>
      selectedIds
        .map((id) => allSubtypeMods.find((mod) => mod.id === id))
        .filter((mod): mod is EditorModifier => Boolean(mod)),
    [allSubtypeMods, selectedIds],
  );

  const selectedBuckets = useMemo(
    () => getSelectedBuckets(selectedMods),
    [selectedMods],
  );

  function resetModifierSelection() {
    setSelectedIds([]);
    setCustomValues({});
    resetPicker();
  }

  useEffect(() => {
    const boundedSocketCount = Math.max(0, Math.min(normalizedMaxSocketCount, socketCount));
    const legalSocketCount = legalSocketCountForCorruptionState(
      boundedSocketCount,
      isCorrupted,
    );
    if (legalSocketCount !== socketCount) setSocketCount(legalSocketCount);
    setSelectedIds((ids) => {
      const sanitized = sanitizeSelectionIdsForCorruptionState({
        selectedIds: ids,
        allMods: allSubtypeMods,
        nextCorrupted: isCorrupted,
        socketCapacity: legalSocketCount,
      });
      return sameOrderedIds(ids, sanitized) ? ids : sanitized;
    });
  }, [isCorrupted, socketCount, allSubtypeMods, normalizedMaxSocketCount]);

  function changeCorrupted(nextValue: boolean) {
    setIsCorrupted(nextValue);
    if (!nextValue) {
      setSocketCount((current) =>
        socketCountAfterCorruptedChange(current, nextValue),
      );
      setSelectedIds((ids) =>
        sanitizeSelectionIdsForCorruptionState({
          selectedIds: ids,
          allMods: allSubtypeMods,
          nextCorrupted: nextValue,
          socketCapacity: socketCountAfterCorruptedChange(socketCount, nextValue),
        }),
      );
    }
  }

  function changeSocketCount(nextValue: number) {
    const nextSocketCount = Math.max(0, Math.min(normalizedMaxSocketCount, Number.isFinite(nextValue) ? nextValue : 0));
    setSocketCount(nextSocketCount);
    setSelectedIds((ids) =>
      trimSocketSelectionIds(ids, allSubtypeMods, nextSocketCount),
    );
    setIsCorrupted((current) =>
      corruptedAfterSocketCountChange(current, nextSocketCount),
    );
  }

  function selectModifier(id: string) {
    const selectedMod = allSubtypeMods.find((mod) => mod.id === id);
    if (selectedMod) {
      setIsCorrupted((current) =>
        corruptedAfterModifierSelection(current, selectedMod.sourceMechanic),
      );
    }
    setSelectedIds((current) => {
      if (selectedMod?.sourceMechanic === "augment" || selectedMod?.sourceMechanic === "bonded") {
        return [...current, id];
      }
      return current.includes(id) ? current : [...current, id];
    });
    closePicker();
  }

  function onValueChange(modId: string, index: number, value: string) {
    const sanitized = value
      .replace(/[^0-9.\-]/g, "")
      .replace(/(\..*)\./g, "$1");
    setCustomValues((current) => ({
      ...current,
      [modId]: {
        ...(current[modId] ?? {}),
        [index]: sanitized,
      },
    }));
  }

  function removeSelected(id: string) {
    setSelectedIds((ids) => {
      const index = ids.indexOf(id);
      if (index < 0) return ids;
      return [...ids.slice(0, index), ...ids.slice(index + 1)];
    });
  }

  function resetItemModifierState() {
    setIsCorrupted(false);
    setSocketCount(Math.min(2, normalizedMaxSocketCount));
    setIsSanctified(false);
    resetModifierSelection();
  }

  function restoreModifierSnapshot(snapshot: EquippedItemDraft) {
    setIsCorrupted(snapshot.isCorrupted);
    setSocketCount(Math.max(0, Math.min(normalizedMaxSocketCount, snapshot.socketCount)));
    setIsSanctified(snapshot.isSanctified);
    setSelectedIds(snapshot.selectedIds);
    setCustomValues(snapshot.customValues);
    resetPicker();
  }

  return {
    changeCorrupted,
    changeSocketCount,
    customValues,
    isCorrupted,
    isSanctified,
    onValueChange,
    removeSelected,
    resetItemModifierState,
    restoreModifierSnapshot,
    resetModifierSelection,
    selectedBuckets,
    selectedIds,
    selectedMods,
    selectModifier,
    setIsCorrupted,
    setIsSanctified,
    setSocketCount,
    socketCount,
  };
}
