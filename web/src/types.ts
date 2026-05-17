export type TooltipSection =
  | { kind: "title"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "property"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "requirement"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "implicit"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "explicit"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "flavour"; lines: string[]; condition?: never; bonded?: never }
  | { kind: "description"; lines: string[]; condition?: never; bonded?: never }
  | {
      kind: "augment_effect";
      condition: "martial_weapon" | "wand_or_staff" | "armour" | string;
      bonded: boolean;
      lines: string[];
    };

export type NormalizedStat = {
  id: string;
  min: number | null;
  max: number | null;
  scope?: "Local" | "Global" | string | null;
  raw: string;
};

export type NormalizedMod = {
  text: string;
  family?: string | null;
  domains?: string | null;
  generationType?: string | null;
  requiredLevel?: number | null;
  stats: NormalizedStat[];
  craftTags: string[];
};

export type ParseStatus = "ok" | "warning";

export type Diagnostic = {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  actionRequired: boolean;
};

export type PlannerEntityBase = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  name: string;
  baseType: string | null;
  itemClass: string | null;
  icon: string | null;
  tooltipSections: TooltipSection[];
  objectData?: Record<string, unknown>;
  parseStatus: ParseStatus;
  warnings: string[];
  diagnostics: Diagnostic[];
};

export type PlannerItem = PlannerEntityBase & {
  kind: "item";
  rarity: string | null;
  frameType: number | null;
  mods: NormalizedMod[];
  normalized?: Record<string, unknown>;
};

export type AugmentEffect = {
  condition: string;
  label?: string | null;
  bonded: boolean;
  text: string;
};

export type PlannerAugment = PlannerEntityBase & {
  kind: "augment";
  augmentEffects: AugmentEffect[];
  augmentCategory?: string | null;
  plannerVisibility?: string | null;
};


export type AugmentSocketCandidateWarning = {
  severity: "error" | "warning" | "info" | string;
  code: string;
  augmentName?: string;
  section?: string;
  message: string;
};

export type AugmentSocketCandidateAudit = {
  total: number;
  socketCandidateCount: number;
  catalogueOnlyCount: number;
  runeItemCandidates: number;
  soulCoreCandidates: number;
  otherSocketableAugments: number;
  excludedReferenceEntries: number;
  socketCandidatesBySection: Record<string, number>;
  socketCandidatesByCategory: Record<string, number>;
  socketCandidatesByReason: Record<string, number>;
  candidateNamesSample: string[];
  warningCounts?: Record<string, number>;
  validationWarnings: AugmentSocketCandidateWarning[];
  complete: boolean;
};

export type AugmentCatalogueEntry = {
  id: string;
  slug: string;
  name: string;
  sourceUrl: string;
  source: "poe2db";
  kind: "augment_catalogue_entry";
  section: string;
  category: string;
  socketCandidate: boolean;
  socketCandidateReason?: string | null;
  plannerVisibility?: "socket_picker" | "catalogue_only" | string;
  detailStatus?: "index_only" | "detail_loaded" | "detail_failed" | string;
  detailSource?: string;
  detailFetchedFromCache?: boolean | null;
  detailName?: string | null;
  detailError?: string | null;
  itemClass?: string | null;
  normalEffectCount?: number;
  bondedEffectCount?: number;
  effectConditions?: string[];
  propertyLines?: string[];
  requirementLines?: string[];
  descriptionLineCount?: number;
  detailWarnings?: string[];
  icon?: string | null;
};

export type AugmentCatalogue = {
  kind: "augment_catalogue";
  source: "poe2db";
  sourceUrl: string;
  generatedFrom: "augment_index" | string;
  entries: AugmentCatalogueEntry[];
  total: number;
  socketCandidateCount: number;
  detailLoadedCount?: number;
  detailFailedCount?: number;
  indexOnlyCount?: number;
  entriesWithEffects?: number;
  detailStatusCounts?: Record<string, number>;
  detailSourceCounts?: Record<string, number>;
  sectionCounts: Record<string, number>;
  categoryCounts: Record<string, number>;
  socketCandidateAudit?: AugmentSocketCandidateAudit;
  warnings: string[];
};

export type AugmentCatalogueSectionAudit = {
  section: string;
  expected?: number | null;
  discovered: number;
  categoryCounts: Record<string, number>;
  socketCandidateCount: number;
  entries: AugmentCatalogueEntry[];
  warnings: string[];
};

export type AugmentIndexAuditWarning = {
  severity: "error" | "warning" | "info" | string;
  code: string;
  section?: string;
  message: string;
};

export type AugmentIndexAudit = {
  expectedTotal: number;
  discoveredTotal: number;
  complete: boolean;
  sections: AugmentCatalogueSectionAudit[];
  categoryCounts: Record<string, number>;
  warningCounts?: Record<string, number>;
  validationWarnings?: AugmentIndexAuditWarning[];
};

export type AugmentValidationWarning = {
  severity: "error" | "warning" | "info" | string;
  code: string;
  augmentName?: string;
  message: string;
};

export type BaseItemSummary = {
  name: string;
  socketCapacity?: number | null;
  maxAugmentSockets?: number | null;
  compatibleSlots?: string[];
  requirements: Record<string, number | null>;
  defences: Record<string, number>;
  properties?: Record<string, unknown>;
  propertyLines?: string[];
  implicitMods?: ItemModifierLine[];
  icon?: string | null;
  sourceUrl?: string | null;
  itemClass?: string | null;
};

export type BaseItem = BaseItemSummary & {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: "base_item";
  itemClass: string;
  parseStatus: ParseStatus;
  warnings: string[];
  diagnostics: Diagnostic[];
};

export type ModifierPoolMod = {
  id: string;
  text: string;
  sourceGroup: string;
  tags: string[];
  keywords: string[];
};

export type ModifierGroup = {
  id: string;
  kind: "planner_corrupted_enchantment_pool" | "reference_vaal_orb_corrupted_enchantment";
  sourceUrl: string;
  itemClass: string;
  subtype: string;
  sourceSection: string;
  sourceGroup: string;
  plannerPrimary: boolean;
  mods: ModifierPoolMod[];
};

export type ModPoolComparison = {
  primary: string;
  reference: string;
  status: string;
  extraInPrimary: string[];
  missingFromPrimary: string[];
};

export type ItemSubtype = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: "item_subtype";
  itemClass: string;
  subtype: string;
  label: string;
  attributeProfile: string[];
  defenceProfile: string[];
  baseItems: BaseItemSummary[];
  modGroups: ModifierGroup[];
  modPoolComparisons: ModPoolComparison[];
  parseStatus: ParseStatus;
  warnings: string[];
  diagnostics: Diagnostic[];
};

export type ItemClassSummary = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: "item_class";
  itemClass: string;
  summary: Record<string, number | null>;
  knownSubtypeSlugs: string[];
  sampleUniqueLabels: string[];
  parseStatus: ParseStatus;
  warnings: string[];
  diagnostics: Diagnostic[];
};

export type EditableValueRange = {
  index: number;
  min: number | null;
  max: number | null;
  value: number | null;
  rangeText: string | null;
  valuePrefix: string;
  valueSuffix: string;
};

export type NormalExplicitAffix = {
  id: string;
  text: string;
  textTemplate?: string | null;
  displayRangeText?: string | null;
  editableValues: EditableValueRange[];
  affixType: "prefix" | "suffix";
  sourceGroup: string;
  family: string | null;
  generationGroup: string | null;
  weightRaw: string | null;
  weightPercent: string | null;
  level: number | null;
  tierCount: number | null;
  detailStatus: "available" | "not_available_from_snapshot";
  tags: string[];
  keywords: string[];
  sourceUrl: string;
};

export type NormalExplicitPool = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: "normal_explicit_pool";
  itemClass: string;
  subtype: string;
  sourceSection: string;
  sourceGroups: string[];
  plannerPrimary: boolean;
  validationSource: string;
  confidence: "low" | "medium" | "high";
  prefixes: NormalExplicitAffix[];
  suffixes: NormalExplicitAffix[];
  diagnostics: Diagnostic[];
  rawSectionNames: string[];
  rawSources: string[];
};

export type EditorModifier = {
  id: string;
  text: string;
  textTemplate?: string | null;
  displayRangeText?: string | null;
  pickerLabel?: string | null;
  pickerGroup?: string | null;
  socketPickerGroup?: string | null;
  sortLabel?: string | null;
  searchText?: string | null;
  runeName?: string | null;
  augmentId?: string | null;
  augmentName?: string | null;
  augmentCategory?: string | null;
  augmentSourceUrl?: string | null;
  socketStatText?: string | null;
  fixedValue?: boolean;
  editableValues: EditableValueRange[];
  sourceGroup: string;
  sourceMechanic: string;
  affixType: "prefix" | "suffix" | null;
  family: string | null;
  generationGroup: string | null;
  weightRaw: string | null;
  weightPercent: string | null;
  level: number | null;
  tierCount: number | null;
  detailStatus: "available" | "not_available_from_snapshot";
  tags: string[];
  keywords: string[];
  sourceUrl: string;
};

export type EditorModifierPool = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: "editor_modifier_pool";
  itemClass: string;
  subtype: string;
  sourceSection: string;
  sourceGroup: string;
  sourceMechanic: EditorModifier["sourceMechanic"];
  affixType: "prefix" | "suffix" | null;
  plannerPrimary: boolean;
  validationSource: string;
  confidence: "low" | "medium" | "high";
  mods: EditorModifier[];
  diagnostics: Diagnostic[];
  rawSource: string;
};


export type ItemModifierLine = {
  id: string;
  text: string;
};

export type UniqueItem = {
  id: string;
  slug: string;
  source: "poe2db";
  sourceUrl: string;
  kind: string;
  name: string;
  baseType: string | null;
  itemClass: string;
  rarity: "Unique";
  icon: string | null;
  socketCapacity?: number | null;
  maxAugmentSockets?: number | null;
  compatibleSlots?: string[];
  requirements: Record<string, number | null>;
  defences: Record<string, unknown>;
  implicitMods: ItemModifierLine[];
  explicitMods: ItemModifierLine[];
  flavourText: string[];
  tooltipSections: TooltipSection[];
  parseStatus: ParseStatus;
  warnings: string[];
  diagnostics: Diagnostic[];
};

export type ModifierSourceMechanic = {
  id: EditorModifierPool["sourceMechanic"];
  label: string;
  order: number;
};

export type DataSnapshot = {
  id: string;
  sourceUrl: string;
  snapshotPath: string;
  fromCache: boolean;
};

export type ParserSanityReport = {
  loadedGloveBases: number;
  loadedBootBases?: number;
  loadedHelmetBases?: number;
  discoveredUniqueGloves: number;
  importedUniqueGloves: number;
  importedUniqueBoots?: number;
  discoveredUniqueHelmets?: number;
  importedUniqueHelmets?: number;
  uniqueHelmetsWithoutExplicitMods?: number;
  uniqueGlovesWithoutExplicitMods: number;
  uniqueGlovesWithoutSourceUrl: number;
  uniqueGlovesWithFlavourText?: number;
  uniqueBootsWithFlavourText?: number;
  uniqueBootsWithoutFlavourText?: number;
  uniqueHelmetsWithFlavourText?: number;
  uniqueItemsWithFlavourText?: number;
  uniqueItemsWithoutFlavourText?: number;
  importedUniqueItems?: number;
  importedUniqueItemClasses?: number;
  uniqueItemsByClass?: Record<string, number>;
  weaponUniqueItemsByClass?: Record<string, number>;
  importedWeaponUniqueItems?: number;
  importedWeaponUniqueItemClasses?: number;
  importedBaseItems?: number;
  importedBaseItemClasses?: number;
  baseItemsByClass?: Record<string, number>;
  loadedAugments?: number;
  loadedSocketAugments?: number;
  loadedRuneAugments?: number;
  expectedRuneAugments?: number;
  discoveredRuneAugments?: number;
  importedRuneAugments?: number;
  importedRuneAugmentsWithNormalEffects?: number;
  importedRuneAugmentsWithAllNormalConditions?: number;
  importedRuneAugmentsWithBondedEffects?: number;
  importedRuneAugmentsWithIcons?: number;
  importedRuneAugmentsWithRequirements?: number;
  augmentIndexWarnings?: string[];
  augmentIndexAudit?: AugmentIndexAudit;
  loadedAugmentCatalogueEntries?: number;
  augmentCatalogueSocketCandidates?: number;
  augmentCatalogueDetailLoaded?: number;
  augmentCatalogueDetailFailed?: number;
  augmentCatalogueIndexOnly?: number;
  augmentCatalogueEntriesWithEffects?: number;
  augmentCatalogueBySection?: Record<string, number>;
  augmentCatalogueByCategory?: Record<string, number>;
  augmentCatalogueDetailStatusCounts?: Record<string, number>;
  augmentCatalogueDetailSourceCounts?: Record<string, number>;
  augmentSocketCandidateAudit?: AugmentSocketCandidateAudit;
  socketAugmentWarnings?: string[];
  augmentCoverage?: {
    expected: number;
    loaded: number;
    discovered: number;
    complete: boolean;
    withNormalEffects: number;
    withBondedEffects: number;
    withIcons: number;
    withRequirements: number;
    withCompleteNormalConditionSets?: number;
    conditions: string[];
    missingNormalEffects: string[];
    missingBondedEffects: string[];
    missingIcons: string[];
    missingRequirements: string[];
    missingNormalConditions?: Record<string, string>;
    suspiciousEffectTexts?: Record<string, string[]>;
    emptyStackSizeProperties?: string[];
    duplicatePropertyLines?: Record<string, string[]>;
    dataSourceCounts?: Record<string, number>;
    warningCounts?: Record<string, number>;
    validationWarnings?: AugmentValidationWarning[];
    warnings: string[];
  };
  loadedEditorModifierPools: number;
  loadedBootEditorModifierPools?: number;
  loadedBootNormalExplicitPools?: number;
  loadedBodyArmourEditorModifierPools?: number;
  loadedBodyArmourNormalExplicitPools?: number;
  loadedHelmetEditorModifierPools?: number;
  loadedHelmetNormalExplicitPools?: number;
  loadedRingEditorModifierPools?: number;
  loadedRingNormalExplicitPools?: number;
  loadedAmuletEditorModifierPools?: number;
  loadedAmuletNormalExplicitPools?: number;
  loadedBeltEditorModifierPools?: number;
  loadedBeltNormalExplicitPools?: number;
  loadedShieldEditorModifierPools?: number;
  loadedShieldNormalExplicitPools?: number;
  loadedFocusEditorModifierPools?: number;
  loadedFocusNormalExplicitPools?: number;
  loadedQuiverEditorModifierPools?: number;
  loadedQuiverNormalExplicitPools?: number;
};


export type PayloadHealthCoverage = {
  total: number;
  withValue: number;
  missing: number;
  missingNames: string[];
};

export type PayloadHealthUniqueClassReport = {
  total: number;
  icon: PayloadHealthCoverage;
  flavourText: PayloadHealthCoverage;
  explicitMods: PayloadHealthCoverage;
  baseType: PayloadHealthCoverage;
  sourceUrl: PayloadHealthCoverage;
};

export type PayloadHealthWarning = {
  severity: "info" | "warning" | "error" | string;
  code: string;
  message: string;
  [key: string]: unknown;
};

export type ModifierCoverageClassReport = {
  itemClass: string;
  supportState: "required" | "experimental" | "unsupported" | string;
  coverageStatus: string;
  note: string;
  requirements: {
    editorModifierPools: boolean;
    normalExplicitPools: boolean;
  };
  missingRequired: string[];
  baseItems: {
    total: number;
    coveredByEditorPools: number;
    coveredByNormalExplicitPools: number;
  };
  uniqueItems: {
    total: number;
    coveredByEditorPools: number;
    coveredByNormalExplicitPools: number;
  };
  itemSubtypes: { total: number };
  editor: { pools: number; mods: number };
  normalExplicit: { pools: number; prefixes: number; suffixes: number };
  sourceUrl?: string;
  sourceUrls?: string[];
  snapshotStatus?: {
    classPage?: string;
    classPagePath?: string | null;
    modifiersCalc?: string;
    modifiersCalcPath?: string | null;
    modifiersCalcPaths?: string[];
    modifiersCalcPresent?: number | null;
    modifiersCalcExpected?: number | null;
    modifiersCalcMissingSlugs?: string[];
  };
};

export type ItemEditorBindingClassReport = {
  itemClass: string;
  status: "ok" | "not_visible" | "missing_binding" | "missing_visible_options" | string;
  expectedItemOptionsFromAudit?: number;
  hasExpectedItemOptions?: boolean;
  baseOptions: number;
  uniqueOptions: number;
  totalItemOptions: number;
  bindableItemOptions?: number;
  resolvedSubtypes: string[];
  editorPools: number;
  normalExplicitPools: number;
  optionsWithEditorPools: number;
  optionsWithNormalExplicitPools: number;
  untypedSpecialItemOptions?: number;
  untypedSpecialOptions?: Array<Record<string, string>>;
  missingEditorPoolOptions: Array<Record<string, string>>;
  missingNormalExplicitPoolOptions: Array<Record<string, string>>;
};

export type ItemEditorExcludedClassReport = {
  itemClass: string;
  status: "ok" | "excluded_class_visible" | string;
  baseOptions: number;
  uniqueOptions: number;
  editorPools: number;
  normalExplicitPools: number;
};

export type ItemEditorBindingReport = {
  status: "ok" | "error" | string;
  summary: {
    requiredClasses: number;
    requiredClassesOk: number;
    itemOptions: number;
    bindableItemOptions?: number;
    optionsWithEditorPools: number;
    optionsWithNormalExplicitPools: number;
    untypedSpecialItemOptions?: number;
    missingEditorPoolOptions: number;
    missingNormalExplicitPoolOptions: number;
    missingVisibleItemClasses: number;
    excludedClassesVisible: number;
  };
  byClass: Record<string, ItemEditorBindingClassReport>;
  excludedClasses: Record<string, ItemEditorExcludedClassReport>;
};

export type ModifierCoverageReport = {
  supportConfig: Record<string, {
    supportState: "required" | "experimental" | "unsupported" | string;
    requireEditorModifierPools: boolean;
    requireNormalExplicitPools: boolean;
    note: string;
  }>;
  summary: {
    requiredClasses: number;
    requiredClassesOk: number;
    experimentalClasses: number;
    experimentalClassesReady: number;
    classesWithEditorPools: number;
    classesWithNormalExplicitPools: number;
  };
  byClass: Record<string, ModifierCoverageClassReport>;
};

export type PayloadHealthReport = {
  status: "ok" | "warning" | "error" | string;
  generatedAt: string;
  schemaVersion: string;
  parserVersion: string;
  uniqueItems: {
    total: number;
    byClass: Record<string, PayloadHealthUniqueClassReport>;
    duplicateNames: Array<{ name: string; count: number }>;
  };
  baseItems?: {
    total: number;
    byClass: Record<string, Record<string, unknown>>;
    duplicateNames: Array<{ name: string; count: number }>;
  };
  itemSubtypes: Record<string, unknown>;
  modifierPools: {
    editor: { poolCount: number; modCount: number; byClass: Record<string, { pools: number; mods: number }> };
    normalExplicit: { poolCount: number; prefixCount: number; suffixCount: number; byClass: Record<string, { pools: number; prefixes: number; suffixes: number }> };
  };
  modifierCoverage?: ModifierCoverageReport;
  itemEditorBinding?: ItemEditorBindingReport;
  warnings: PayloadHealthWarning[];
};

export type PlannerItemOptionContract = {
  id: string;
  kind: "base" | "unique";
  itemClass: string;
  label: string;
  name: string;
  baseName: string;
  subtype?: string | null;
  resolvedSubtype?: string | null;
  subtypeKey?: string | null;
  uniqueId?: string | null;
  icon?: string | null;
  compatibleSlots?: string[];
  socketCapacity?: number | null;
  maxAugmentSockets?: number | null;
  searchText?: string | null;
};

export type PlannerSlotCompatibilityEntry = {
  slot?: string;
  id?: string;
  itemClasses?: string[];
  acceptsItemClasses?: string[];
  compatibleItemClasses?: string[];
};

export type PlannerEquipmentSlotContract = PlannerSlotCompatibilityEntry & {
  label?: string;
  maxSockets?: number | null;
};

export type PlannerSocketCapacityContract = {
  defaultMaxSockets?: number | null;
  maxSocketCount?: number | null;
  defaultSocketCount?: number | null;
  itemClassMaxSockets?: Record<string, number | null>;
  itemClassSocketLimits?: Record<string, number | null>;
};

export type PlannerUiContract = {
  itemOptions?: PlannerItemOptionContract[];
  slotCompatibility?: Record<string, string[]> | PlannerSlotCompatibilityEntry[];
  equipmentSlots?: PlannerEquipmentSlotContract[];
  socketCapacity?: PlannerSocketCapacityContract;
  socketLimits?: PlannerSocketCapacityContract;
  itemClassSocketLimits?: Record<string, number | null>;
  itemEditor?: {
    itemOptions?: PlannerItemOptionContract[];
    slotCompatibility?: Record<string, string[]> | PlannerSlotCompatibilityEntry[];
    equipmentSlots?: PlannerEquipmentSlotContract[];
    socketCapacity?: PlannerSocketCapacityContract;
    socketLimits?: PlannerSocketCapacityContract;
  };
};

export type PlannerPocData = {
  schemaVersion: string;
  parserVersion: string;
  generatedAt: string;
  source: "poe2db";
  sourceUrls: string[];
  items: PlannerItem[];
  augment?: PlannerAugment;
  augments: PlannerAugment[];
  augmentCatalogue?: AugmentCatalogue | null;
  itemClasses: ItemClassSummary[];
  itemSubtypes: ItemSubtype[];
  normalExplicitPools: NormalExplicitPool[];
  editorModifierPools: EditorModifierPool[];
  modifierSourceMechanics: ModifierSourceMechanic[];
  baseItems: BaseItem[];
  uniqueItems: UniqueItem[];
  itemOptions?: PlannerItemOptionContract[];
  dataSnapshots?: DataSnapshot[];
  parserSanity?: ParserSanityReport;
  payloadHealth?: PayloadHealthReport;
  ui?: PlannerUiContract;
  equipmentSlots?: PlannerEquipmentSlotContract[];
  slotCompatibility?: Record<string, string[]> | PlannerSlotCompatibilityEntry[];
  socketCapacity?: PlannerSocketCapacityContract;
  socketLimits?: PlannerSocketCapacityContract;
  itemClassSocketLimits?: Record<string, number | null>;
};
