import { useEffect, useMemo, useState } from "react";
import type { BaseItem, ItemSubtype, PlannerItemOptionContract, UniqueItem } from "../../../types";
import {
  type ItemClassOption,
  type ItemOption,
} from "../domain/equipment";
import { inferSubtypeFromBaseItem } from "../domain/itemDefences";

function baseOptionId(base: Pick<BaseItem, "itemClass" | "name">): string {
  return `base:${base.itemClass}:${base.name}`;
}

function uniqueOptionId(item: Pick<UniqueItem, "id">): string {
  return `unique:${item.id}`;
}

function normalizeGeneratedItemOption(option: PlannerItemOptionContract): ItemOption | null {
  if (!option.id || !option.itemClass || !option.name || !option.baseName) return null;
  const subtype = option.resolvedSubtype ?? option.subtype ?? option.subtypeKey ?? "base";
  return {
    id: option.id,
    kind: option.kind,
    itemClass: option.itemClass,
    label: option.label || option.name,
    name: option.name,
    baseName: option.baseName,
    subtype: subtype || "base",
    uniqueId: option.uniqueId ?? undefined,
    icon: option.icon ?? null,
    compatibleSlots: option.compatibleSlots,
    socketCapacity: option.socketCapacity ?? option.maxAugmentSockets ?? null,
    searchText: option.searchText ?? null,
  };
}

function sortItemOptions(options: ItemOption[]): ItemOption[] {
  return [...options].sort((a, b) => {
    const classCompare = a.itemClass.localeCompare(b.itemClass);
    if (classCompare) return classCompare;
    if (a.kind !== b.kind) return a.kind === "unique" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

export function useItemCatalog({
  subtypes,
  baseItems,
  uniqueItems,
  generatedItemOptions,
}: {
  subtypes: ItemSubtype[];
  baseItems: BaseItem[];
  uniqueItems: UniqueItem[];
  generatedItemOptions?: PlannerItemOptionContract[];
}) {
  const normalizedGeneratedOptions = useMemo(
    () =>
      (generatedItemOptions ?? [])
        .map(normalizeGeneratedItemOption)
        .filter((option): option is ItemOption => Boolean(option))
        .filter((option) => option.itemClass !== "Traps"),
    [generatedItemOptions],
  );

  const [selectedItemClass, setSelectedItemClass] = useState<ItemClassOption>(
    () =>
      normalizedGeneratedOptions[0]?.itemClass ??
      subtypes[0]?.itemClass ??
      baseItems[0]?.itemClass ??
      uniqueItems[0]?.itemClass ??
      "",
  );

  const baseByClassAndName = useMemo(() => {
    const map = new Map<string, BaseItem>();
    for (const base of baseItems) map.set(`${base.itemClass}\0${base.name}`, base);
    return map;
  }, [baseItems]);

  const fallbackGlobalItemOptions = useMemo<ItemOption[]>(() => {
    const baseOptions = baseItems
      .filter((base) => base.itemClass !== "Traps")
      .map((base) => ({
        id: baseOptionId(base),
        kind: "base" as const,
        itemClass: base.itemClass,
        label: base.name,
        name: base.name,
        baseName: base.name,
        subtype: inferSubtypeFromBaseItem(base, base.itemClass),
        icon: base.icon ?? null,
        compatibleSlots: base.compatibleSlots,
        socketCapacity: base.socketCapacity ?? base.maxAugmentSockets ?? null,
      }));
    const uniqueOptions = uniqueItems
      .filter((item) => item.itemClass !== "Traps")
      .map((item) => {
        const baseName = item.baseType ?? item.name;
        const base = baseByClassAndName.get(`${item.itemClass}\0${baseName}`);
        return {
          id: uniqueOptionId(item),
          kind: "unique" as const,
          itemClass: item.itemClass,
          label: `${item.name} (${baseName})`,
          name: item.name,
          baseName,
          subtype: inferSubtypeFromBaseItem(base, item.itemClass),
          uniqueId: item.id,
          icon: item.icon ?? base?.icon ?? null,
          compatibleSlots: item.compatibleSlots ?? base?.compatibleSlots,
          socketCapacity: item.socketCapacity ?? item.maxAugmentSockets ?? base?.socketCapacity ?? base?.maxAugmentSockets ?? null,
        };
      });
    return sortItemOptions([...baseOptions, ...uniqueOptions]);
  }, [baseByClassAndName, baseItems, uniqueItems]);

  const globalItemOptions = useMemo(
    () =>
      normalizedGeneratedOptions.length
        ? sortItemOptions(normalizedGeneratedOptions)
        : fallbackGlobalItemOptions,
    [fallbackGlobalItemOptions, normalizedGeneratedOptions],
  );

  const availableItemClasses = useMemo(
    () => Array.from(new Set(globalItemOptions.map((option) => option.itemClass))).filter(Boolean),
    [globalItemOptions],
  );

  useEffect(() => {
    if (
      availableItemClasses.length &&
      !availableItemClasses.includes(selectedItemClass)
    ) {
      setSelectedItemClass(availableItemClasses[0]);
    }
  }, [availableItemClasses, selectedItemClass]);

  const subtypeOptions = useMemo(
    () => subtypes.filter((subtype) => subtype.itemClass === selectedItemClass),
    [selectedItemClass, subtypes],
  );

  const classBaseItems = useMemo(
    () => baseItems.filter((item) => item.itemClass === selectedItemClass),
    [baseItems, selectedItemClass],
  );

  const selectedClassUniqueItems = useMemo(
    () => uniqueItems.filter((item) => item.itemClass === selectedItemClass),
    [selectedItemClass, uniqueItems],
  );

  const fallbackClassItemOptions = useMemo<ItemOption[]>(() => {
    const baseItemSubtypeMap = new Map<string, string>();
    for (const subtype of subtypeOptions) {
      for (const base of subtype.baseItems)
        if (!baseItemSubtypeMap.has(base.name)) baseItemSubtypeMap.set(base.name, subtype.subtype);
    }
    for (const base of classBaseItems) {
      if (!baseItemSubtypeMap.has(base.name))
        baseItemSubtypeMap.set(base.name, inferSubtypeFromBaseItem(base, selectedItemClass));
    }

    const baseOptions = subtypeOptions.length
      ? subtypeOptions.flatMap((subtype) =>
          subtype.baseItems.map((base) => {
            const matchingBase = classBaseItems.find((item) => item.name === base.name);
            return {
              id: `base:${selectedItemClass}:${base.name}`,
              kind: "base" as const,
              itemClass: selectedItemClass,
              label: base.name,
              name: base.name,
              baseName: base.name,
              subtype: subtype.subtype,
              icon: base.icon ?? matchingBase?.icon ?? null,
              compatibleSlots: base.compatibleSlots ?? matchingBase?.compatibleSlots,
              socketCapacity: base.socketCapacity ?? base.maxAugmentSockets ?? matchingBase?.socketCapacity ?? matchingBase?.maxAugmentSockets ?? null,
            };
          }),
        )
      : classBaseItems.map((base) => ({
          id: baseOptionId(base),
          kind: "base" as const,
          itemClass: selectedItemClass,
          label: base.name,
          name: base.name,
          baseName: base.name,
          subtype: inferSubtypeFromBaseItem(base, selectedItemClass),
          icon: base.icon ?? null,
          compatibleSlots: base.compatibleSlots,
          socketCapacity: base.socketCapacity ?? base.maxAugmentSockets ?? null,
        }));
    const uniqueOptions = selectedClassUniqueItems
      .filter((item) => item.name)
      .map((item) => {
        const base = baseByClassAndName.get(`${item.itemClass}\0${item.baseType ?? ""}`);
        return {
          id: uniqueOptionId(item),
          kind: "unique" as const,
          itemClass: selectedItemClass,
          label: item.name,
          name: item.name,
          baseName: item.baseType ?? item.name,
          subtype:
            baseItemSubtypeMap.get(item.baseType ?? "") ??
            inferSubtypeFromBaseItem(base, item.itemClass),
          uniqueId: item.id,
          icon: item.icon ?? base?.icon ?? null,
          compatibleSlots: item.compatibleSlots ?? base?.compatibleSlots,
          socketCapacity: item.socketCapacity ?? item.maxAugmentSockets ?? base?.socketCapacity ?? base?.maxAugmentSockets ?? null,
        };
      });
    return [...baseOptions, ...uniqueOptions];
  }, [baseByClassAndName, classBaseItems, selectedClassUniqueItems, selectedItemClass, subtypeOptions]);

  const itemOptions = useMemo(
    () =>
      normalizedGeneratedOptions.length
        ? normalizedGeneratedOptions.filter((option) => option.itemClass === selectedItemClass)
        : fallbackClassItemOptions,
    [fallbackClassItemOptions, normalizedGeneratedOptions, selectedItemClass],
  );

  return {
    availableItemClasses,
    classBaseItems,
    globalItemOptions,
    itemOptions,
    selectedClassUniqueItems,
    selectedItemClass,
    setSelectedItemClass,
    subtypeOptions,
  };
}
