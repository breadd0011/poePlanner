import type { EditorModifierPool } from "../../../../types";

export type SourceLabelMap = Record<string, string>;
export type PickerKind = "enchant" | "explicit" | "socket" | null;
export type PanelMode = "browser" | "editor";
export type BrowserKindFilter = "all" | "base" | "unique";

export const PICKER_LABELS: Record<Exclude<PickerKind, null>, string> = {
  enchant: "Add Enchant Mod",
  explicit: "Add Explicit Mod",
  socket: "Add Socket Item",
};

export function pickerSources(
  kind: Exclude<PickerKind, null>,
): EditorModifierPool["sourceMechanic"][] {
  if (kind === "enchant") return ["corrupted"];
  if (kind === "socket") return ["augment"];
  return ["normal", "essence", "perfect_essence", "desecrated"];
}

export function pickerDescription(kind: Exclude<PickerKind, null>): string {
  if (kind === "enchant")
    return "Corrupted / enchant-style options compatible with this base.";
  if (kind === "socket")
    return "Compatible augment socket options from the selected item type ModifiersCalc page.";
  return "Normal, essence, perfect essence, and desecrated explicit-style modifiers.";
}
