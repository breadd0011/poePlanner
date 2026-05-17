import type { Rarity } from "./equipment";

export type ItemEditorWarningInput = {
  selectedNormalPrefixes: number;
  selectedNormalSuffixes: number;
  rarity: Rarity;
  selectedModifierCount: number;
  hasSelectedUnique: boolean;
  selectedItemClass: string;
  isCorrupted: boolean;
  selectedEnchantCount: number;
  safeQuality: number;
  selectedSocketCount: number;
  socketCapacity: number;
};

export function getItemEditorSoftWarnings({
  selectedNormalPrefixes,
  selectedNormalSuffixes,
  rarity,
  selectedModifierCount,
  hasSelectedUnique,
  selectedItemClass,
  isCorrupted,
  selectedEnchantCount,
  safeQuality,
  selectedSocketCount,
  socketCapacity,
}: ItemEditorWarningInput): string[] {
  return [
    selectedNormalPrefixes > 3
      ? `You selected ${selectedNormalPrefixes} normal prefixes. This preview does not enforce item slot limits.`
      : null,
    selectedNormalSuffixes > 3
      ? `You selected ${selectedNormalSuffixes} normal suffixes. This preview does not enforce item slot limits.`
      : null,
    rarity === "Normal" && selectedModifierCount > 0
      ? "Normal rarity selected, but modifiers are present. This is display-only for now."
      : null,
    rarity === "Unique" && !hasSelectedUnique
      ? `Unique rarity selected, but the selected item is a base ${selectedItemClass.slice(0, -1).toLowerCase()}. This is display-only for now.`
      : null,
    !isCorrupted && selectedEnchantCount > 0
      ? "Corrupted/enchant-like modifiers are selected while Corrupted is unchecked."
      : null,
    safeQuality > 20
      ? "Quality above 20 is treated as extended quality, usually from special sources such as Vaal Infuser."
      : null,
    selectedSocketCount > socketCapacity
      ? `You selected ${selectedSocketCount} socket items, but the current socket capacity is ${socketCapacity}.`
      : null,
  ].filter((warning): warning is string => Boolean(warning));
}
