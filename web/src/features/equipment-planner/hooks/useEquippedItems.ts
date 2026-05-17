import { useState } from "react";
import type { EquippedPreview, SlotKey } from "../domain/equipment";

export function useEquippedItems() {
  const [equipped, setEquipped] = useState<
    Partial<Record<SlotKey, EquippedPreview>>
  >({});

  function equipItem(slot: SlotKey, preview: EquippedPreview) {
    setEquipped((current) => ({ ...current, [slot]: preview }));
  }

  return { equipped, equipItem };
}
