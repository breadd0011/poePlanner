import { useMemo, useState } from "react";
import type { BaseItem, ItemSubtype, UniqueItem } from "../../../types";
import type { EquippedItemDraft, ItemClassOption, ItemOption, Rarity } from "../domain/equipment";

export function useItemEditorDraft({
  classBaseItems,
  itemOptions,
  selectedClassUniqueItems,
  selectedItemClass,
  subtypeOptions,
}: {
  classBaseItems: BaseItem[];
  itemOptions: ItemOption[];
  selectedClassUniqueItems: UniqueItem[];
  selectedItemClass: ItemClassOption;
  subtypeOptions: ItemSubtype[];
}) {
  const [selectedItemId, setSelectedItemId] = useState("");
  const [subtypeKey, setSubtypeKey] = useState(
    subtypeOptions.find((subtype) => subtype.subtype === "int")?.subtype ??
      subtypeOptions[0]?.subtype ??
      "",
  );
  const [baseName, setBaseName] = useState("");
  const [customName, setCustomName] = useState("");
  const [rarity, setRarity] = useState<Rarity>("Normal");
  const [selectedUniqueId, setSelectedUniqueId] = useState("");
  const [itemLevel, setItemLevel] = useState(100);
  const [quality, setQuality] = useState(20);

  const selectedItemOption = useMemo(
    () => itemOptions.find((candidate) => candidate.id === selectedItemId) ?? null,
    [itemOptions, selectedItemId],
  );

  const subtype = useMemo(
    () => subtypeOptions.find((candidate) => candidate.subtype === subtypeKey),
    [subtypeKey, subtypeOptions],
  );

  const selectedUnique = useMemo(
    () =>
      selectedClassUniqueItems.find((item) => item.id === selectedUniqueId) ??
      null,
    [selectedUniqueId, selectedClassUniqueItems],
  );

  const selectedSubtypeKey = subtype?.subtype ?? "";
  const selectedBase =
    subtype?.baseItems.find((base) => base.name === baseName) ??
    classBaseItems.find((base) => base.name === baseName) ??
    subtype?.baseItems[0] ??
    classBaseItems[0];
  const displayName =
    customName.trim() ||
    selectedUnique?.name ||
    selectedBase?.name ||
    selectedItemClass;
  const safeQuality = Math.max(0, Math.min(30, quality));

  function applyItemOption(
    option: ItemOption,
    onSubtypeChanged?: () => void,
  ) {
    const subtypeChanged = option.subtype !== subtypeKey;
    setSelectedItemId(option.id);
    setSubtypeKey(option.subtype);
    setBaseName(option.baseName);
    if (option.kind === "unique" && option.uniqueId) {
      setSelectedUniqueId(option.uniqueId);
      setRarity("Unique");
    } else {
      setSelectedUniqueId("");
      setRarity("Normal");
    }
    setCustomName("");
    if (subtypeChanged) onSubtypeChanged?.();
  }

  function selectItemOption(
    optionId: string,
    onSubtypeChanged?: () => void,
  ) {
    const option = itemOptions.find((candidate) => candidate.id === optionId);
    if (!option) return;
    applyItemOption(option, onSubtypeChanged);
  }

  function selectPreferredItemOption() {
    if (!itemOptions.length) return;
    const preferred =
      itemOptions.find((option) => option.kind === "base") ?? itemOptions[0];
    setSelectedItemId(preferred.id);
    setSubtypeKey(preferred.subtype);
    setBaseName(preferred.baseName);
    setSelectedUniqueId(
      preferred.kind === "unique" ? (preferred.uniqueId ?? "") : "",
    );
    setRarity(preferred.kind === "unique" ? "Unique" : "Normal");
  }

  function resetDraftForItemClassChange() {
    setSelectedItemId("");
    setBaseName("");
    setCustomName("");
    setSelectedUniqueId("");
    setRarity("Normal");
    setItemLevel(100);
    setQuality(20);
  }

  function restoreDraftSnapshot(snapshot: EquippedItemDraft) {
    setSelectedItemId(snapshot.selectedItemId);
    const option = itemOptions.find(
      (candidate) => candidate.id === snapshot.selectedItemId,
    );
    setSubtypeKey(option?.subtype ?? snapshot.selectedSubtypeKey ?? subtypeKey);
    setBaseName(option?.baseName ?? snapshot.selectedBaseName ?? baseName);
    setSelectedUniqueId(
      option?.kind === "unique"
        ? (option.uniqueId ?? "")
        : (snapshot.selectedUniqueId ?? ""),
    );
    setCustomName(snapshot.customName);
    setRarity(snapshot.rarity);
    setItemLevel(snapshot.itemLevel);
    setQuality(snapshot.quality);
  }

  return {
    customName,
    displayName,
    itemLevel,
    quality,
    rarity,
    resetDraftForItemClassChange,
    restoreDraftSnapshot,
    safeQuality,
    selectItemOption,
    selectItemOptionDirect: applyItemOption,
    selectPreferredItemOption,
    selectedBase,
    selectedItemId,
    selectedItemOption,
    selectedSubtypeKey,
    selectedUnique,
    selectedUniqueId,
    setCustomName,
    setItemLevel,
    setQuality,
    setRarity,
    setSelectedItemId,
    setSelectedUniqueId,
    subtype,
    subtypeKey,
  };
}
