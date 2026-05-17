import { useState } from "react";
import type { ItemOption, SlotKey } from "../domain/equipment";
import type { BrowserKindFilter, PanelMode, PickerKind } from "../components/item-editor/editorTypes";

export function useItemEditorModal({
  setPickerKind,
}: {
  setPickerKind: (kind: PickerKind) => void;
}) {
  const [activeSlot, setActiveSlot] = useState<SlotKey | null>(null);
  const [panelMode, setPanelMode] = useState<PanelMode>("browser");
  const [browserQuery, setBrowserQuery] = useState("");
  const [browserKind, setBrowserKind] =
    useState<BrowserKindFilter>("all");
  const [pendingBrowserSelection, setPendingBrowserSelection] =
    useState<ItemOption | null>(null);

  function openEquipmentSlot(slot: SlotKey, mode: PanelMode = "browser") {
    setActiveSlot(slot);
    setPanelMode(mode);
    setBrowserQuery("");
    setBrowserKind("all");
    setPendingBrowserSelection(null);
    setPickerKind(null);
  }

  function closePlannerModal() {
    setActiveSlot(null);
    setPanelMode("browser");
    setBrowserQuery("");
    setBrowserKind("all");
    setPendingBrowserSelection(null);
    setPickerKind(null);
  }

  function openEditorForBrowserOption(option: ItemOption) {
    setPendingBrowserSelection(option);
    setPanelMode("editor");
  }

  function clearPendingBrowserSelection() {
    setPendingBrowserSelection(null);
  }

  return {
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
  };
}
