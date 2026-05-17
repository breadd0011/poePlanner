import type { PlannerPocData } from "./types";

export type PayloadContractIssue = {
  severity: "error" | "warning";
  code: string;
  message: string;
};

export class PayloadContractError extends Error {
  issues: PayloadContractIssue[];

  constructor(issues: PayloadContractIssue[]) {
    super(
      issues.length
        ? issues.map((issue) => `${issue.code}: ${issue.message}`).join("\n")
        : "Invalid planner payload",
    );
    this.name = "PayloadContractError";
    this.issues = issues;
  }
}

type RecordLike = Record<string, unknown>;

const REQUIRED_STRING_FIELDS = [
  "schemaVersion",
  "parserVersion",
  "generatedAt",
  "source",
] as const;

const REQUIRED_ARRAY_FIELDS = [
  "sourceUrls",
  "items",
  "itemClasses",
  "itemSubtypes",
  "normalExplicitPools",
  "editorModifierPools",
  "modifierSourceMechanics",
  "baseItems",
  "uniqueItems",
] as const;

function isRecord(value: unknown): value is RecordLike {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function hasArrayField(record: RecordLike, field: string): boolean {
  return Array.isArray(record[field]);
}

function hasObjectField(record: RecordLike, field: string): boolean {
  return isRecord(record[field]);
}

function hasAnyRecordPath(record: RecordLike, paths: string[][]): boolean {
  return paths.some((path) => {
    let current: unknown = record;
    for (const segment of path) {
      if (!isRecord(current)) return false;
      current = current[segment];
    }
    return isRecord(current) || Array.isArray(current);
  });
}

function hasRuntimeSlotCompatibility(record: RecordLike): boolean {
  return hasAnyRecordPath(record, [
    ["slotCompatibility"],
    ["equipmentSlots"],
    ["ui", "slotCompatibility"],
    ["ui", "equipmentSlots"],
    ["ui", "itemEditor", "slotCompatibility"],
    ["ui", "itemEditor", "equipmentSlots"],
  ]);
}

function hasRuntimeSocketConfig(record: RecordLike): boolean {
  return hasAnyRecordPath(record, [
    ["socketCapacity"],
    ["socketLimits"],
    ["itemClassSocketLimits"],
    ["ui", "socketCapacity"],
    ["ui", "socketLimits"],
    ["ui", "itemClassSocketLimits"],
    ["ui", "itemEditor", "socketCapacity"],
    ["ui", "itemEditor", "socketLimits"],
  ]);
}

function hasRuntimeItemOptions(record: RecordLike): boolean {
  return hasAnyRecordPath(record, [
    ["itemOptions"],
    ["ui", "itemOptions"],
    ["ui", "itemEditor", "itemOptions"],
  ]);
}

export function validatePlannerPayload(payload: unknown): {
  data: PlannerPocData;
  issues: PayloadContractIssue[];
} {
  const issues: PayloadContractIssue[] = [];

  if (!isRecord(payload)) {
    throw new PayloadContractError([
      {
        severity: "error",
        code: "payload_not_object",
        message: "Planner data must be a JSON object.",
      },
    ]);
  }

  for (const field of REQUIRED_STRING_FIELDS) {
    if (typeof payload[field] !== "string" || !payload[field]) {
      issues.push({
        severity: "error",
        code: `missing_${field}`,
        message: `Planner payload is missing required string field \`${field}\`.`,
      });
    }
  }

  for (const field of REQUIRED_ARRAY_FIELDS) {
    if (!hasArrayField(payload, field)) {
      issues.push({
        severity: "error",
        code: `missing_${field}`,
        message: `Planner payload is missing required array field \`${field}\`.`,
      });
    }
  }

  if (!hasArrayField(payload, "augments")) {
    issues.push({
      severity: "error",
      code: "missing_augments",
      message: "Planner payload must expose an `augments` array; the legacy single `augment` field is no longer enough for runtime UI.",
    });
  }

  if (hasObjectField(payload, "augment")) {
    issues.push({
      severity: "warning",
      code: "legacy_single_augment_present",
      message: "Legacy `augment` field is still present. The UI now reads the canonical `augments` array instead.",
    });
  }

  if (!hasRuntimeSlotCompatibility(payload)) {
    issues.push({
      severity: "warning",
      code: "frontend_default_slot_compatibility",
      message: "Payload does not include slot compatibility metadata yet; the UI is using its visible transitional default map.",
    });
  }

  if (!hasRuntimeSocketConfig(payload)) {
    issues.push({
      severity: "warning",
      code: "frontend_default_socket_limits",
      message: "Payload does not include socket capacity metadata yet; the UI is using its visible transitional default socket limits.",
    });
  }

  if (!hasRuntimeItemOptions(payload)) {
    issues.push({
      severity: "warning",
      code: "frontend_derived_item_options",
      message: "Payload does not include pre-resolved item editor options yet; the UI is deriving item options from base/unique/subtype data.",
    });
  }

  const errors = issues.filter((issue) => issue.severity === "error");
  if (errors.length) throw new PayloadContractError(errors);

  return { data: payload as PlannerPocData, issues };
}
