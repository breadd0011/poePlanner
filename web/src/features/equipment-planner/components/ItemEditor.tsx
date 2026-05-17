import { useMemo } from "react";
import type {
  BaseItem,
  BaseItemSummary,
  EditorModifierPool,
  ItemSubtype,
  ModifierSourceMechanic,
  PlannerAugment,
  PlannerItemOptionContract,
  UniqueItem,
} from "../../../types";
import { getSlotLabel, slotAcceptsItemClass, slotAcceptsOption, type EquippedPreview, type SlotCompatibilityMap } from "../domain/equipment";
import {
  createAugmentLookupIndex,
  resolveAppliedAugmentEffectsForItem,
  resolveSocketAugmentsForMods,
} from "../domain/augmentEffects";
import { adjustedDefences } from "../domain/itemDefences";
import { adjustedItemProperties } from "../domain/itemProperties";
import { computeSocketCapacity, maxSocketCountForItemClass, type SocketCapacityConfig } from "../domain/itemSockets";
import { getItemEditorSoftWarnings } from "../domain/itemValidation";
import { displayKey } from "../domain/itemText";
import { EquipmentBoard } from "./item-editor/EquipmentBoard";
import { ItemBrowser } from "./item-editor/ItemBrowser";
import { ModalShell } from "./item-editor/ModalShell";
import { ItemTooltipPreview } from "./item-editor/ItemTooltipPreview";
import { ItemEditorHeaderForm } from "./item-editor/ItemEditorHeaderForm";
import { ItemEditorActions } from "./item-editor/ItemEditorActions";
import { ItemEditorWarnings } from "./item-editor/ItemEditorWarnings";
import { ModifierPicker } from "./item-editor/ModifierPicker";
import { SocketCategory, StatCategory } from "./item-editor/StatCategories";
import { type PickerKind, type SourceLabelMap } from "./item-editor/editorTypes";
import { useItemCatalog } from "../hooks/useItemCatalog";
import { useModifierPicker } from "../hooks/useModifierPicker";
import { useEquippedItems } from "../hooks/useEquippedItems";
import { useItemEditorModal } from "../hooks/useItemEditorModal";
import { useItemModifierState } from "../hooks/useItemModifierState";
import { useItemEditorDraft } from "../hooks/useItemEditorDraft";
import { useItemEditorSelectionFlow } from "../hooks/useItemEditorSelectionFlow";

function formatRequirements(base: BaseItemSummary | undefined): string[] {
  if (!base) return [];
  return Object.entries(base.requirements)
    .filter(([, value]) => value !== null)
    .map(
      ([key, value]) =>
        `${key === "level" ? "Level" : key.toUpperCase()} ${value}`,
    );
}

export function ItemEditor({
  subtypes,
  pools,
  baseItems,
  uniqueItems,
  sourceMechanics,
  augments,
  slotCompatibility,
  socketConfig,
  generatedItemOptions,
}: {
  subtypes: ItemSubtype[];
  pools: EditorModifierPool[];
  baseItems: BaseItem[];
  uniqueItems: UniqueItem[];
  sourceMechanics: ModifierSourceMechanic[];
  augments: PlannerAugment[];
  slotCompatibility?: SlotCompatibilityMap;
  socketConfig?: SocketCapacityConfig;
  generatedItemOptions?: PlannerItemOptionContract[];
}) {
  const {
    availableItemClasses,
    classBaseItems,
    globalItemOptions,
    itemOptions,
    selectedClassUniqueItems,
    selectedItemClass,
    setSelectedItemClass,
    subtypeOptions,
  } = useItemCatalog({ subtypes, baseItems, uniqueItems, generatedItemOptions });

  const {
    customName,
    displayName,
    itemLevel,
    quality,
    rarity,
    resetDraftForItemClassChange,
    restoreDraftSnapshot,
    safeQuality,
    selectItemOption: applyItemOptionSelection,
    selectItemOptionDirect: applyBrowserItemOptionSelection,
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
    subtypeKey,
  } = useItemEditorDraft({
    classBaseItems,
    itemOptions,
    selectedClassUniqueItems,
    selectedItemClass,
    subtypeOptions,
  });
  const subtypePools = useMemo(
    () =>
      pools.filter((pool) => {
        if (pool.itemClass !== selectedItemClass || pool.mods.length === 0)
          return false;
        // Armour classes use explicit itemSubtypes. Class-level pages use
        // subtype="base". Shields have no itemSubtypes in the payload, but
        // expose PoE2DB modifier pages by defence profile, so the selected
        // base/unique item infers subtype="str"/"str_dex"/"str_int".
        if (!subtypeOptions.length) {
          return (
            pool.subtype === subtypeKey ||
            pool.subtype === "base" ||
            pool.subtype === ""
          );
        }
        return pool.subtype === subtypeKey;
      }),
    [pools, selectedItemClass, subtypeKey, subtypeOptions.length],
  );
  const sourceLabels = useMemo<SourceLabelMap>(() => {
    const labels: SourceLabelMap = {};
    for (const source of sourceMechanics) labels[source.id] = source.label;
    for (const pool of pools) {
      if (!labels[pool.sourceMechanic])
        labels[pool.sourceMechanic] = displayKey(pool.sourceMechanic);
    }
    return labels;
  }, [pools, sourceMechanics]);

  const sourceOrder = useMemo(() => {
    const configured = [...sourceMechanics]
      .sort((a, b) => a.order - b.order)
      .map((source) => source.id);
    const observed = Array.from(
      new Set(pools.map((pool) => pool.sourceMechanic)),
    );
    return [
      ...configured,
      ...observed.filter((source) => !configured.includes(source)),
    ];
  }, [pools, sourceMechanics]);

  const augmentIndex = useMemo(() => createAugmentLookupIndex(augments), [augments]);

  const {
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
  } = useModifierPicker({ subtypePools, sourceOrder, selectedItemClass, augmentIndex });

  const {
    activeSlot,
    browserKind,
    browserQuery,
    clearPendingBrowserSelection,
    closePlannerModal,
    openEditorForBrowserOption,
    openEquipmentSlot,
    panelMode,
    pendingBrowserSelection,
    setBrowserKind,
    setBrowserQuery,
    setPanelMode,
  } = useItemEditorModal({ setPickerKind });
  const { equipped, equipItem } = useEquippedItems();

  const activeSlotLabel = activeSlot ? getSlotLabel(activeSlot) : "";
  const browserClassOptions = useMemo(() => {
    if (!activeSlot) return [];
    return availableItemClasses
      .filter((itemClass) => slotAcceptsItemClass(activeSlot, itemClass, slotCompatibility))
      .filter((itemClass) =>
        globalItemOptions.some((option) => option.itemClass === itemClass),
      );
  }, [activeSlot, availableItemClasses, globalItemOptions, slotCompatibility]);
  const visibleBrowserOptions = useMemo(() => {
    if (!activeSlot) return [];
    const normalizedQuery = browserQuery.trim().toLowerCase();
    return globalItemOptions.filter((option) => {
      if (!slotAcceptsOption(activeSlot, option, slotCompatibility)) return false;
      if (browserKind !== "all" && option.kind !== browserKind) return false;
      if (normalizedQuery) {
        const searchable =
          (option.searchText ?? `${option.name} ${option.baseName} ${option.itemClass} ${option.kind}`).toLowerCase();
        if (!searchable.includes(normalizedQuery)) return false;
      }
      return true;
    });
  }, [activeSlot, browserKind, browserQuery, globalItemOptions, slotCompatibility]);

  const {
    changeCorrupted,
    changeSocketCount,
    customValues,
    isCorrupted,
    isSanctified,
    onValueChange,
    removeSelected,
    resetItemModifierState,
    resetModifierSelection,
    restoreModifierSnapshot,
    selectedBuckets,
    selectedIds,
    selectedMods,
    selectModifier,
    setIsSanctified,
    socketCount,
  } = useItemModifierState({
    allSubtypeMods,
    resetPicker,
    closePicker: () => setPickerKind(null),
    maxSocketCount: maxSocketCountForItemClass(selectedItemClass, socketConfig),
  });


  const { openSlot, selectBrowserOption, selectItemOption } = useItemEditorSelectionFlow({
    equipped,
    itemOptions,
    pendingBrowserSelection,
    selectedItemClass,
    selectedItemId,
    setSelectedItemClass,
    openEquipmentSlot,
    openEditorForBrowserOption,
    clearPendingBrowserSelection,
    applyItemOptionSelection,
    applyBrowserItemOptionSelection,
    selectPreferredItemOption,
    resetDraftForItemClassChange,
    resetModifierSelection,
    resetItemModifierState,
    restoreDraftSnapshot,
    restoreModifierSnapshot,
  });


  const selectedBasePropertyLines = adjustedItemProperties(
    selectedBase,
    quality,
    selectedMods,
    selectedUnique?.explicitMods ?? [],
    customValues,
  );
  const selectedBaseImplicitMods = selectedUnique
    ? []
    : (selectedBase?.implicitMods ?? []);
  const socketAugments = useMemo(
    () => resolveSocketAugmentsForMods(selectedBuckets.sockets, augmentIndex),
    [augmentIndex, selectedBuckets.sockets],
  );
  const appliedSocketEffects = useMemo(
    () =>
      resolveAppliedAugmentEffectsForItem({
        itemClass: selectedItemClass,
        socketMods: selectedBuckets.sockets,
        lookup: augmentIndex,
      }),
    [augmentIndex, selectedBuckets.sockets, selectedItemClass],
  );
  const socketCapacity = computeSocketCapacity({
    itemClass: selectedItemClass,
    selectedBase,
    selectedUnique,
    selectedOption: selectedItemOption,
    selectedSocketCount: socketCount,
    socketConfig,
  });
  const equippedPreview: EquippedPreview = {
    name: displayName,
    baseName:
      selectedBase?.name ?? selectedUnique?.baseType ?? selectedItemClass,
    itemClass: selectedItemClass,
    rarity,
    icon: selectedUnique?.icon ?? selectedBase?.icon ?? null,
    socketCapacity,
    socketFilledCount: selectedBuckets.sockets.length,
    socketAugments,
    draft: {
      customName,
      customValues,
      isCorrupted,
      isSanctified,
      itemLevel,
      quality,
      rarity,
      selectedBaseName:
        selectedBase?.name ?? selectedUnique?.baseType ?? selectedItemClass,
      selectedIds,
      selectedItemClass,
      selectedItemId,
      selectedSubtypeKey: selectedSubtypeKey || subtypeKey || "base",
      selectedUniqueId,
      socketCount,
    },
  };
  function confirmEquipActiveItem() {
    if (!activeSlot) return;
    equipItem(activeSlot, equippedPreview);
    closePlannerModal();
  }
  const defenceLines = adjustedDefences(
    selectedBase,
    quality,
    selectedMods,
    selectedUnique?.explicitMods ?? [],
    customValues,
    sourceLabels,
  );
  const requirementParts = formatRequirements(selectedBase);
  const selectedNormalPrefixes = selectedMods.filter(
    (mod) => mod.sourceMechanic === "normal" && mod.affixType === "prefix",
  ).length;
  const selectedNormalSuffixes = selectedMods.filter(
    (mod) => mod.sourceMechanic === "normal" && mod.affixType === "suffix",
  ).length;
  const softWarnings = getItemEditorSoftWarnings({
    selectedNormalPrefixes,
    selectedNormalSuffixes,
    rarity,
    selectedModifierCount: selectedMods.length,
    hasSelectedUnique: Boolean(selectedUnique),
    selectedItemClass,
    isCorrupted,
    selectedEnchantCount: selectedBuckets.enchant.length,
    safeQuality,
    selectedSocketCount: selectedBuckets.sockets.length,
    socketCapacity,
  });

  function openPicker(kind: Exclude<PickerKind, null>) {
    setPickerKind(kind);
  }

  return (
    <section className="simple-editor planner-layout-shell">
      <EquipmentBoard equipped={equipped} openSlot={openSlot} />

      {!activeSlot ? (
        <section className="planner-empty-state">
          <strong>
            Select an equipment slot to browse PoE2DB-backed base and unique
            items.
          </strong>
          <p>
            The existing PoE-style tooltip/editor is preserved inside the item
            editor modal.
          </p>
        </section>
      ) : null}

      {activeSlot && panelMode === "browser" ? (
        <ModalShell
          title="Item Browser"
          subtitle={`${activeSlotLabel} items only`}
          onClose={closePlannerModal}
          wide
        >
          <ItemBrowser
            activeSlotLabel={activeSlotLabel}
            query={browserQuery}
            kind={browserKind}
            visibleOptions={visibleBrowserOptions}
            compatibleClassCount={browserClassOptions.length}
            onQueryChange={setBrowserQuery}
            onKindChange={setBrowserKind}
            onSelect={selectBrowserOption}
          />
        </ModalShell>
      ) : null}

      {activeSlot && panelMode === "editor" ? (
        <ModalShell
          title="Item Editor"
          onClose={closePlannerModal}
        >
          <section className="planner-editor-shell item-editor-shell planner-editor-modal-body">
            <ItemEditorActions
              onBackToBrowser={() => setPanelMode("browser")}
              onEquip={confirmEquipActiveItem}
            />
            <div className="item-editor-layout">
              <div className="item-editor-form-column">
                <ItemEditorHeaderForm
                  customName={customName}
                  isCorrupted={isCorrupted}
                  isSanctified={isSanctified}
                  itemLevel={itemLevel}
                  itemOptions={itemOptions}
                  rarity={rarity}
                  safeQuality={safeQuality}
                  selectedItemId={selectedItemId}
                  selectedSocketCount={socketCount}
                  maxSocketCount={maxSocketCountForItemClass(selectedItemClass, socketConfig)}
                  onCorruptedChange={changeCorrupted}
                  onCustomNameChange={setCustomName}
                  onItemLevelChange={setItemLevel}
                  onItemSelect={selectItemOption}
                  onQualityChange={setQuality}
                  onRarityChange={setRarity}
                  onSanctifiedChange={setIsSanctified}
                  onSocketCountChange={changeSocketCount}
                />


                <div className="item-editor-sections item-editor-sections--properties">
                  <StatCategory
                    title="Enchant"
                    mods={selectedBuckets.enchant}
                    customValues={customValues}
                    addLabel="Add Enchant Mod"
                    onAdd={() => openPicker("enchant")}
                    onRemove={removeSelected}
                    onValueChange={onValueChange}
                  />
                  <StatCategory
                    title="Explicit"
                    mods={selectedBuckets.explicit}
                    uniqueMods={selectedUnique?.explicitMods ?? []}
                    customValues={customValues}
                    addLabel="Add Explicit Mod"
                    onAdd={() => openPicker("explicit")}
                    onRemove={removeSelected}
                    onValueChange={onValueChange}
                  />
                  <SocketCategory
                    mods={selectedBuckets.sockets}
                    customValues={customValues}
                    capacity={socketCapacity}
                    onAdd={() => openPicker("socket")}
                    onRemove={removeSelected}
                    onValueChange={onValueChange}
                  />
                </div>

                <ItemEditorWarnings warnings={softWarnings} />
              </div>

              <aside className="item-editor-preview-column">
                <ItemTooltipPreview
                  customName={customName}
                  customValues={customValues}
                  defenceLines={defenceLines}
                  displayName={displayName}
                  iconPath={selectedUnique?.icon ?? selectedBase?.icon ?? null}
                  isCorrupted={isCorrupted}
                  isSanctified={isSanctified}
                  itemLevel={itemLevel}
                  propertyLines={selectedBasePropertyLines}
                  requirementParts={requirementParts}
                  selectedBaseImplicitMods={selectedBaseImplicitMods}
                  selectedBaseName={
                    selectedBase?.name ??
                    selectedUnique?.baseType ??
                    selectedItemClass
                  }
                  selectedBuckets={selectedBuckets}
                  selectedItemClass={selectedItemClass}
                  selectedUnique={selectedUnique}
                  rarity={rarity}
                  safeQuality={safeQuality}
                  socketCapacity={socketCapacity}
                  socketFilledCount={selectedBuckets.sockets.length}
                  socketAugments={socketAugments}
                  appliedSocketEffects={appliedSocketEffects}
                />
              </aside>
            </div>
          </section>
        </ModalShell>
      ) : null}

      {pickerKind ? (
        <ModifierPicker
          kind={pickerKind}
          mods={visiblePickerMods}
          availableSources={pickerAvailableSources}
          activeSources={
            activePickerSources.length
              ? activePickerSources
              : pickerAvailableSources
          }
          sourceCounts={sourceCounts}
          sourceLabels={sourceLabels}
          selectedIds={selectedIds}
          customValues={customValues}
          augmentIndex={augmentIndex}
          query={pickerQuery}
          activeTag={pickerTag}
          tagOptions={pickerTagOptions}
          onQueryChange={setPickerQuery}
          onTagChange={setPickerTag}
          onToggleSource={togglePickerSource}
          onSelect={selectModifier}
          onClose={() => setPickerKind(null)}
        />
      ) : null}
    </section>
  );
}
