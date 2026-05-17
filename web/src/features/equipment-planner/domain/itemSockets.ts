import type { EditorModifier, PlannerPocData, UniqueItem } from "../../../types";
import type { ItemClassOption } from "./equipment";

export type SocketCapacityConfig = {
  defaultMaxSockets: number;
  defaultSocketCount: number;
  itemClassMaxSockets: Record<string, number>;
};

const DEFAULT_MAX_AUGMENT_SOCKETS = 6;
const DEFAULT_SOCKET_COUNT = 2;

const DEFAULT_SOCKET_CAPACITY_CONFIG: SocketCapacityConfig = {
  defaultMaxSockets: DEFAULT_MAX_AUGMENT_SOCKETS,
  defaultSocketCount: DEFAULT_SOCKET_COUNT,
  itemClassMaxSockets: {},
};

type RecordLike = Record<string, unknown>;
type SocketCapacitySource = {
  socketCapacity?: number | null;
  maxAugmentSockets?: number | null;
  explicitMods?: Array<{ text: string }>;
  objectData?: Record<string, unknown>;
} | null | undefined;

function isRecord(value: unknown): value is RecordLike {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function finitePositiveInteger(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(0, Math.floor(value));
}

function numericRecordValues(value: unknown): Record<string, number> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).flatMap(([key, raw]) => {
      const parsed = finitePositiveInteger(raw);
      return parsed === null ? [] : [[key, parsed]];
    }),
  );
}

function socketConfigObjects(data: PlannerPocData): RecordLike[] {
  return [
    data.ui?.itemEditor?.socketCapacity,
    data.ui?.itemEditor?.socketLimits,
    data.ui?.socketCapacity,
    data.ui?.socketLimits,
    data.socketCapacity,
    data.socketLimits,
  ].filter(isRecord);
}

export function createSocketCapacityConfig(data?: PlannerPocData): SocketCapacityConfig {
  if (!data) return DEFAULT_SOCKET_CAPACITY_CONFIG;

  const config: SocketCapacityConfig = {
    ...DEFAULT_SOCKET_CAPACITY_CONFIG,
    itemClassMaxSockets: {},
  };

  for (const source of socketConfigObjects(data)) {
    const defaultMax = finitePositiveInteger(source.defaultMaxSockets ?? source.maxSocketCount);
    if (defaultMax !== null) config.defaultMaxSockets = defaultMax;

    const defaultSocketCount = finitePositiveInteger(source.defaultSocketCount);
    if (defaultSocketCount !== null) config.defaultSocketCount = defaultSocketCount;

    Object.assign(
      config.itemClassMaxSockets,
      numericRecordValues(source.itemClassMaxSockets),
      numericRecordValues(source.itemClassSocketLimits),
    );
  }

  Object.assign(config.itemClassMaxSockets, numericRecordValues(data.itemClassSocketLimits));

  return config;
}

export function maxSocketCountForItemClass(
  itemClass: ItemClassOption,
  config: SocketCapacityConfig = DEFAULT_SOCKET_CAPACITY_CONFIG,
): number {
  return config.itemClassMaxSockets[itemClass] ?? config.defaultMaxSockets;
}

export function defaultSocketCount(
  itemClass: ItemClassOption,
  config: SocketCapacityConfig = DEFAULT_SOCKET_CAPACITY_CONFIG,
): number {
  return Math.min(config.defaultSocketCount, maxSocketCountForItemClass(itemClass, config));
}

export function getSelectedBuckets(mods: EditorModifier[]) {
  return {
    enchant: mods.filter((mod) => mod.sourceMechanic === "corrupted"),
    explicit: mods.filter((mod) =>
      ["normal", "essence", "perfect_essence", "desecrated"].includes(
        mod.sourceMechanic,
      ),
    ),
    sockets: mods.filter((mod) =>
      ["augment", "bonded"].includes(mod.sourceMechanic),
    ),
  };
}

export function socketCapacityFromText(text: string): number | null {
  const match = text.match(/has\s+(\d+)\s+augment\s+sockets?/i);
  if (!match) return null;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

function socketCapacityFromObjectData(item: SocketCapacitySource): number | null {
  if (!item || !isRecord(item.objectData)) return null;
  return (
    finitePositiveInteger(item.objectData.socketCapacity) ??
    finitePositiveInteger(item.objectData.maxAugmentSockets) ??
    finitePositiveInteger(item.objectData.augmentSocketCount)
  );
}

function explicitSocketCapacityFromItem(item: SocketCapacitySource): number | null {
  if (!item) return null;

  const direct =
    finitePositiveInteger(item.socketCapacity) ??
    finitePositiveInteger(item.maxAugmentSockets) ??
    socketCapacityFromObjectData(item);
  if (direct !== null) return direct;

  let capacity: number | null = null;
  for (const mod of item.explicitMods ?? []) {
    const explicitCapacity = socketCapacityFromText(mod.text);
    if (explicitCapacity !== null) capacity = Math.max(capacity ?? 0, explicitCapacity);
  }
  return capacity;
}

export function computeSocketCapacity({
  itemClass,
  selectedBase,
  selectedUnique,
  selectedOption,
  selectedSocketCount,
  socketConfig = DEFAULT_SOCKET_CAPACITY_CONFIG,
}: {
  itemClass: ItemClassOption;
  selectedBase?: SocketCapacitySource;
  selectedUnique: UniqueItem | null;
  selectedOption?: SocketCapacitySource;
  selectedSocketCount: number;
  socketConfig?: SocketCapacityConfig;
}): number {
  const maxSocketCount = maxSocketCountForItemClass(itemClass, socketConfig);
  let capacity = Math.max(0, Math.min(maxSocketCount, selectedSocketCount));

  const itemCapacity =
    explicitSocketCapacityFromItem(selectedOption) ??
    explicitSocketCapacityFromItem(selectedUnique) ??
    explicitSocketCapacityFromItem(selectedBase);
  if (itemCapacity !== null) capacity = Math.max(capacity, itemCapacity);

  return Math.max(0, Math.min(maxSocketCount, capacity));
}

export type SocketSelectionMod = Pick<EditorModifier, "id" | "sourceMechanic">;

export function isSocketModifier(mod: SocketSelectionMod): boolean {
  return ["augment", "bonded"].includes(mod.sourceMechanic);
}

export function sameOrderedIds(left: string[], right: string[]): boolean {
  return (
    left.length === right.length &&
    left.every((id, index) => id === right[index])
  );
}

export function trimSocketSelectionIds(
  selectedIds: string[],
  allMods: SocketSelectionMod[],
  capacity: number,
): string[] {
  let socketIndex = 0;
  return selectedIds.filter((id) => {
    const mod = allMods.find((candidate) => candidate.id === id);
    if (!mod || !isSocketModifier(mod)) return true;
    socketIndex += 1;
    return socketIndex <= capacity;
  });
}

export function sanitizeSelectionIdsForCorruptionState({
  selectedIds,
  allMods,
  nextCorrupted,
  socketCapacity,
}: {
  selectedIds: string[];
  allMods: SocketSelectionMod[];
  nextCorrupted: boolean;
  socketCapacity: number;
}): string[] {
  const withoutIllegalCorruptionMods = nextCorrupted
    ? selectedIds
    : selectedIds.filter((id) => {
        const mod = allMods.find((candidate) => candidate.id === id);
        return mod?.sourceMechanic !== "corrupted";
      });
  return trimSocketSelectionIds(
    withoutIllegalCorruptionMods,
    allMods,
    socketCapacity,
  );
}

export function legalSocketCountForCorruptionState(
  socketCount: number,
  isCorrupted: boolean,
): number {
  return isCorrupted ? socketCount : Math.min(socketCount, 2);
}

export function socketCountAfterCorruptedChange(
  previousSocketCount: number,
  nextCorrupted: boolean,
): number {
  return nextCorrupted ? previousSocketCount : Math.min(previousSocketCount, 2);
}

export function corruptedAfterSocketCountChange(
  previousCorrupted: boolean,
  selectedSocketCount: number,
): boolean {
  return selectedSocketCount >= 3 ? true : previousCorrupted;
}

export function corruptedAfterModifierSelection(
  previousCorrupted: boolean,
  sourceMechanic: EditorModifier["sourceMechanic"],
): boolean {
  return sourceMechanic === "corrupted" ? true : previousCorrupted;
}
