import {
  PayloadContractError,
  type PayloadContractIssue,
  validatePlannerPayload,
} from "./dataContract";
import type { PlannerPocData } from "./types";

export type LoadedPlannerData = {
  data: PlannerPocData;
  issues: PayloadContractIssue[];
  source: "monolith" | "split_manifest";
  loadedUrls: string[];
};

type RecordLike = Record<string, unknown>;

type PlannerSplitManifest = {
  kind?: string;
  manifestVersion?: string;
  schemaVersion?: string;
  runtimeData?: unknown;
  runtimeDataUrl?: string;
  dataUrl?: string;
  segments?: Record<string, string | undefined>;
  urls?: Record<string, string | undefined>;
};

const SEGMENT_FIELD_NAMES: Record<string, keyof PlannerPocData> = {
  sourceUrls: "sourceUrls",
  items: "items",
  augments: "augments",
  itemClasses: "itemClasses",
  itemSubtypes: "itemSubtypes",
  normalExplicitPools: "normalExplicitPools",
  editorModifierPools: "editorModifierPools",
  modifierSourceMechanics: "modifierSourceMechanics",
  baseItems: "baseItems",
  uniqueItems: "uniqueItems",
  parserSanity: "parserSanity",
  payloadHealth: "payloadHealth",
  ui: "ui",
  equipmentSlots: "equipmentSlots",
  slotCompatibility: "slotCompatibility",
  socketCapacity: "socketCapacity",
  socketLimits: "socketLimits",
  itemClassSocketLimits: "itemClassSocketLimits",
};

function isRecord(value: unknown): value is RecordLike {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function looksLikeSplitManifest(value: unknown): value is PlannerSplitManifest {
  if (!isRecord(value)) return false;
  if (value.kind === "planner_payload_manifest") return true;
  if (typeof value.manifestVersion === "string" && (isRecord(value.segments) || isRecord(value.urls))) return true;
  if (typeof value.runtimeDataUrl === "string" || typeof value.dataUrl === "string") return true;
  return false;
}

function resolveUrl(url: string, baseUrl: string): string {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  return new URL(url, new URL(baseUrl, origin)).toString();
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

function getSegmentUrl(manifest: PlannerSplitManifest, key: string): string | undefined {
  const directKey = `${key}Url`;
  const manifestRecord = manifest as RecordLike;
  const direct = manifestRecord[directKey];
  if (typeof direct === "string" && direct) return direct;
  const segments = manifest.segments ?? manifest.urls;
  const fromSegments = segments?.[key];
  return typeof fromSegments === "string" && fromSegments ? fromSegments : undefined;
}

async function loadRuntimeRoot(manifest: PlannerSplitManifest, manifestUrl: string, loadedUrls: string[]): Promise<RecordLike> {
  const runtimeUrl = manifest.runtimeDataUrl ?? manifest.dataUrl ?? getSegmentUrl(manifest, "runtimeData") ?? getSegmentUrl(manifest, "runtime");
  if (runtimeUrl) {
    const resolvedUrl = resolveUrl(runtimeUrl, manifestUrl);
    loadedUrls.push(resolvedUrl);
    const runtimeData = await fetchJson(resolvedUrl);
    if (!isRecord(runtimeData)) throw new PayloadContractError([
      {
        severity: "error",
        code: "runtime_data_not_object",
        message: `Split payload runtime data at ${runtimeUrl} must be a JSON object.`,
      },
    ]);
    return { ...runtimeData };
  }

  if (isRecord(manifest.runtimeData)) return { ...manifest.runtimeData };

  throw new PayloadContractError([
    {
      severity: "error",
      code: "missing_runtime_data",
      message: "Split payload manifest must include `runtimeData`, `runtimeDataUrl`, or a runtime segment URL.",
    },
  ]);
}

async function mergeSegmentIfPresent({
  manifest,
  manifestUrl,
  field,
  segmentKey,
  target,
  loadedUrls,
}: {
  manifest: PlannerSplitManifest;
  manifestUrl: string;
  field: keyof PlannerPocData;
  segmentKey: string;
  target: RecordLike;
  loadedUrls: string[];
}) {
  const segmentUrl = getSegmentUrl(manifest, segmentKey);
  if (!segmentUrl) return;
  const resolvedUrl = resolveUrl(segmentUrl, manifestUrl);
  loadedUrls.push(resolvedUrl);
  const segment = await fetchJson(resolvedUrl);
  if (isRecord(segment) && field in segment) {
    target[field] = segment[field as string];
  } else {
    target[field] = segment;
  }
}

async function loadSplitPlannerPayload(manifest: PlannerSplitManifest, manifestUrl: string): Promise<LoadedPlannerData> {
  const loadedUrls = [manifestUrl];
  const data = await loadRuntimeRoot(manifest, manifestUrl, loadedUrls);

  for (const [segmentKey, field] of Object.entries(SEGMENT_FIELD_NAMES)) {
    await mergeSegmentIfPresent({
      manifest,
      manifestUrl,
      field,
      segmentKey,
      target: data,
      loadedUrls,
    });
  }

  const validated = validatePlannerPayload(data);
  return {
    data: validated.data,
    issues: validated.issues,
    source: "split_manifest",
    loadedUrls,
  };
}

export async function loadPlannerData(dataUrl: string): Promise<LoadedPlannerData> {
  const payload = await fetchJson(dataUrl);
  if (looksLikeSplitManifest(payload)) {
    return loadSplitPlannerPayload(payload, dataUrl);
  }

  const validated = validatePlannerPayload(payload);
  return {
    data: validated.data,
    issues: validated.issues,
    source: "monolith",
    loadedUrls: [dataUrl],
  };
}
