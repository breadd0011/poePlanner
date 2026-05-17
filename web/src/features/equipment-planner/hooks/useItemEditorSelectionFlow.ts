import { useEffect, useReducer } from "react";
import type { EquippedItemDraft, ItemClassOption, ItemOption, SlotKey } from "../domain/equipment";
import type { PanelMode } from "../components/item-editor/editorTypes";

type SelectionFlowState = {
  observedItemClass: ItemClassOption;
  skipNextClassReset: boolean;
};

type SelectionFlowAction =
  | { type: "restore_equipped_item" }
  | { type: "observed_item_class_change"; itemClass: ItemClassOption }
  | { type: "consume_restore_skip" };

function selectionFlowReducer(
  state: SelectionFlowState,
  action: SelectionFlowAction,
): SelectionFlowState {
  switch (action.type) {
    case "restore_equipped_item":
      return {
        ...state,
        skipNextClassReset: true,
      };
    case "observed_item_class_change":
      return {
        ...state,
        observedItemClass: action.itemClass,
      };
    case "consume_restore_skip":
      return {
        ...state,
        skipNextClassReset: false,
      };
    default:
      return state;
  }
}

export function useItemEditorSelectionFlow({
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
}: {
  equipped: Partial<Record<SlotKey, { draft?: EquippedItemDraft } | null | undefined>>;
  itemOptions: ItemOption[];
  pendingBrowserSelection: ItemOption | null;
  selectedItemClass: ItemClassOption;
  selectedItemId: string;
  setSelectedItemClass: (itemClass: ItemClassOption) => void;
  openEquipmentSlot: (slot: SlotKey, mode?: PanelMode) => void;
  openEditorForBrowserOption: (option: ItemOption) => void;
  clearPendingBrowserSelection: () => void;
  applyItemOptionSelection: (optionId: string, onSubtypeChanged?: () => void) => void;
  applyBrowserItemOptionSelection: (option: ItemOption, onSubtypeChanged?: () => void) => void;
  selectPreferredItemOption: () => void;
  resetDraftForItemClassChange: () => void;
  resetModifierSelection: () => void;
  resetItemModifierState: () => void;
  restoreDraftSnapshot: (snapshot: EquippedItemDraft) => void;
  restoreModifierSnapshot: (snapshot: EquippedItemDraft) => void;
}) {
  const [flowState, dispatch] = useReducer(selectionFlowReducer, {
    observedItemClass: selectedItemClass,
    skipNextClassReset: false,
  });

  function openSlot(slot: SlotKey) {
    const equippedItem = equipped[slot];
    if (!equippedItem?.draft) {
      openEquipmentSlot(slot);
      return;
    }

    dispatch({
      type: "restore_equipped_item",
    });
    setSelectedItemClass(equippedItem.draft.selectedItemClass);
    restoreDraftSnapshot(equippedItem.draft);
    restoreModifierSnapshot(equippedItem.draft);
    openEquipmentSlot(slot, "editor");
  }

  function selectItemOption(optionId: string) {
    applyItemOptionSelection(optionId, resetModifierSelection);
  }

  function selectBrowserOption(option: ItemOption) {
    openEditorForBrowserOption(option);
    setSelectedItemClass(option.itemClass);
    applyBrowserItemOptionSelection(option, resetModifierSelection);
    resetModifierSelection();
  }

  useEffect(() => {
    if (!pendingBrowserSelection) return;
    if (pendingBrowserSelection.itemClass !== selectedItemClass) return;
    const matchingOption = itemOptions.find((option) => {
      if (option.kind !== pendingBrowserSelection.kind) return false;
      if (option.kind === "unique")
        return option.uniqueId === pendingBrowserSelection.uniqueId;
      return (
        option.baseName === pendingBrowserSelection.baseName ||
        option.name === pendingBrowserSelection.name
      );
    });
    if (!matchingOption) return;
    selectItemOption(matchingOption.id);
    clearPendingBrowserSelection();
  }, [clearPendingBrowserSelection, itemOptions, pendingBrowserSelection, selectedItemClass]);

  useEffect(() => {
    if (!itemOptions.length) return;
    if (pendingBrowserSelection) return;
    if (
      selectedItemId &&
      itemOptions.some((option) => option.id === selectedItemId)
    )
      return;
    selectPreferredItemOption();
  }, [itemOptions, pendingBrowserSelection, selectPreferredItemOption, selectedItemClass, selectedItemId]);

  useEffect(() => {
    if (flowState.observedItemClass === selectedItemClass) return;
    dispatch({ type: "observed_item_class_change", itemClass: selectedItemClass });

    if (flowState.skipNextClassReset) {
      dispatch({ type: "consume_restore_skip" });
      return;
    }

    if (pendingBrowserSelection?.itemClass === selectedItemClass) return;

    resetDraftForItemClassChange();
    resetItemModifierState();
  }, [
    flowState.observedItemClass,
    flowState.skipNextClassReset,
    pendingBrowserSelection,
    resetDraftForItemClassChange,
    resetItemModifierState,
    selectedItemClass,
  ]);

  return {
    openSlot,
    selectBrowserOption,
    selectItemOption,
  };
}
