from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Diagnostic(StrictBaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    actionRequired: bool = False


class NormalizedStat(StrictBaseModel):
    id: str
    min: int | None
    max: int | None
    scope: str | None = None
    raw: str


class NormalizedMod(StrictBaseModel):
    text: str
    family: str | None = None
    domains: str | None = None
    generationType: str | None = None
    requiredLevel: int | None = None
    stats: list[NormalizedStat] = Field(default_factory=list)
    craftTags: list[str] = Field(default_factory=list)


class TooltipSection(StrictBaseModel):
    kind: Literal[
        "title",
        "property",
        "requirement",
        "implicit",
        "explicit",
        "flavour",
        "description",
        "augment_effect",
    ]
    lines: list[str]
    condition: str | None = None
    bonded: bool | None = None

    @field_validator("lines")
    @classmethod
    def no_empty_lines(cls, lines: list[str]) -> list[str]:
        if not lines or any(not str(line).strip() for line in lines):
            raise ValueError("tooltip section lines must be non-empty strings")
        return lines

    @model_validator(mode="after")
    def augment_effect_fields_are_consistent(self) -> "TooltipSection":
        if self.kind == "augment_effect":
            if self.condition is None or self.bonded is None:
                raise ValueError("augment_effect sections require condition and bonded")
        elif self.condition is not None or self.bonded is not None:
            raise ValueError("condition/bonded are only valid for augment_effect sections")
        return self


class PlannerEntityBase(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    name: str
    itemClass: str | None = None
    baseType: str | None = None
    icon: str | None = None
    tooltipSections: list[TooltipSection]
    objectData: dict[str, Any] = Field(default_factory=dict)
    parseStatus: Literal["ok", "warning"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def never_unknown_item(cls, value: str) -> str:
        if value == "Unknown Item" or not value.strip():
            raise ValueError("entity name must be a real parsed/fallback name")
        return value


class PlannerItem(PlannerEntityBase):
    kind: Literal["item"]
    rarity: str | None = None
    frameType: int | None = None
    mods: list[NormalizedMod] = Field(default_factory=list)
    normalized: dict[str, Any] = Field(default_factory=dict)


class AugmentEffect(StrictBaseModel):
    condition: str
    label: str | None = None
    bonded: bool
    text: str

    @field_validator("text")
    @classmethod
    def no_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("augment effect text must not be empty")
        return value


class PlannerAugment(PlannerEntityBase):
    kind: Literal["augment"]
    augmentEffects: list[AugmentEffect] = Field(default_factory=list)
    augmentCategory: str | None = None
    plannerVisibility: str | None = None


class AugmentCatalogueEntry(StrictBaseModel):
    id: str
    slug: str
    name: str
    sourceUrl: str
    source: Literal["poe2db"]
    kind: Literal["augment_catalogue_entry"]
    section: str
    category: str
    socketCandidate: bool = False
    socketCandidateReason: str | None = None
    plannerVisibility: Literal["socket_picker", "catalogue_only"] = "catalogue_only"
    detailStatus: Literal["index_only", "detail_loaded", "detail_failed"] = "index_only"
    detailSource: str = "index_only"
    detailFetchedFromCache: bool | None = None
    detailName: str | None = None
    detailError: str | None = None
    itemClass: str | None = None
    normalEffectCount: int = 0
    bondedEffectCount: int = 0
    effectConditions: list[str] = Field(default_factory=list)
    propertyLines: list[str] = Field(default_factory=list)
    requirementLines: list[str] = Field(default_factory=list)
    descriptionLineCount: int = 0
    detailWarnings: list[str] = Field(default_factory=list)
    icon: str | None = None


class AugmentCatalogue(StrictBaseModel):
    kind: Literal["augment_catalogue"]
    source: Literal["poe2db"]
    sourceUrl: str
    generatedFrom: Literal["augment_index"]
    entries: list[AugmentCatalogueEntry] = Field(default_factory=list)
    total: int = 0
    socketCandidateCount: int = 0
    detailLoadedCount: int = 0
    detailFailedCount: int = 0
    indexOnlyCount: int = 0
    entriesWithEffects: int = 0
    detailStatusCounts: dict[str, int] = Field(default_factory=dict)
    detailSourceCounts: dict[str, int] = Field(default_factory=dict)
    sectionCounts: dict[str, int] = Field(default_factory=dict)
    categoryCounts: dict[str, int] = Field(default_factory=dict)
    socketCandidateAudit: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class BaseItemSummary(StrictBaseModel):
    name: str
    requirements: dict[str, int | None] = Field(default_factory=dict)
    defences: dict[str, int] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    propertyLines: list[str] = Field(default_factory=list)
    implicitMods: list[dict[str, str]] = Field(default_factory=list)
    icon: str | None = None
    sourceUrl: str | None = None
    itemClass: str | None = None


class BaseItem(BaseItemSummary):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: Literal["base_item"]
    itemClass: str
    parseStatus: Literal["ok", "warning"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ModifierPoolMod(StrictBaseModel):
    id: str
    text: str
    sourceGroup: str
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class EditableValueRange(StrictBaseModel):
    index: int
    min: int | float | None = None
    max: int | float | None = None
    value: int | float | None = None
    rangeText: str | None = None
    valuePrefix: str = ""
    valueSuffix: str = ""


class NormalExplicitAffix(StrictBaseModel):
    id: str
    text: str
    textTemplate: str | None = None
    displayRangeText: str | None = None
    editableValues: list[EditableValueRange] = Field(default_factory=list)
    affixType: Literal["prefix", "suffix"]
    sourceGroup: str
    family: str | None = None
    generationGroup: str | None = None
    weightRaw: str | None = None
    weightPercent: str | None = None
    level: int | None = None
    tierCount: int | None = None
    detailStatus: Literal["available", "not_available_from_snapshot"] = "not_available_from_snapshot"
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    sourceUrl: str


class NormalExplicitPool(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: Literal["normal_explicit_pool"]
    itemClass: str
    subtype: str
    sourceSection: str
    sourceGroups: list[str] = Field(default_factory=list)
    plannerPrimary: bool
    validationSource: str
    confidence: Literal["low", "medium", "high"]
    prefixes: list[NormalExplicitAffix] = Field(default_factory=list)
    suffixes: list[NormalExplicitAffix] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    rawSectionNames: list[str] = Field(default_factory=list)
    rawSources: list[str] = Field(default_factory=list)


class EditorModifier(StrictBaseModel):
    id: str
    text: str
    textTemplate: str | None = None
    displayRangeText: str | None = None
    editableValues: list[EditableValueRange] = Field(default_factory=list)
    # Socketable/rune options are fixed-value rows parsed from PoE2DB popup/ModsView data.
    runeName: str | None = None
    socketStatText: str | None = None
    pickerLabel: str | None = None
    augmentId: str | None = None
    augmentName: str | None = None
    augmentCategory: str | None = None
    augmentSourceUrl: str | None = None
    fixedValue: bool = False
    sourceGroup: str
    sourceMechanic: Literal["normal", "desecrated", "essence", "perfect_essence", "augment", "bonded", "corrupted"]
    affixType: Literal["prefix", "suffix"] | None = None
    family: str | None = None
    generationGroup: str | None = None
    weightRaw: str | None = None
    weightPercent: str | None = None
    level: int | None = None
    tierCount: int | None = None
    detailStatus: Literal["available", "not_available_from_snapshot"] = "available"
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    sourceUrl: str


class EditorModifierPool(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: Literal["editor_modifier_pool"]
    itemClass: str
    subtype: str
    sourceSection: str
    sourceGroup: str
    sourceMechanic: Literal["normal", "desecrated", "essence", "perfect_essence", "augment", "bonded", "corrupted"]
    affixType: Literal["prefix", "suffix"] | None = None
    plannerPrimary: bool
    validationSource: str
    confidence: Literal["low", "medium", "high"]
    mods: list[EditorModifier] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    rawSource: str


class ModifierGroup(StrictBaseModel):
    id: str
    kind: Literal["planner_corrupted_enchantment_pool", "reference_vaal_orb_corrupted_enchantment"]
    sourceUrl: str
    itemClass: str
    subtype: str
    sourceSection: str
    sourceGroup: str
    plannerPrimary: bool
    mods: list[ModifierPoolMod] = Field(default_factory=list)


class ModPoolComparison(StrictBaseModel):
    primary: str
    reference: str
    status: str
    extraInPrimary: list[str] = Field(default_factory=list)
    missingFromPrimary: list[str] = Field(default_factory=list)


class ItemSubtype(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: Literal["item_subtype"]
    itemClass: str
    subtype: str
    label: str
    attributeProfile: list[str] = Field(default_factory=list)
    defenceProfile: list[str] = Field(default_factory=list)
    baseItems: list[BaseItemSummary] = Field(default_factory=list)
    modGroups: list[ModifierGroup] = Field(default_factory=list)
    modPoolComparisons: list[ModPoolComparison] = Field(default_factory=list)
    parseStatus: Literal["ok", "warning"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ItemClassSummary(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: Literal["item_class"]
    itemClass: str
    summary: dict[str, int | None] = Field(default_factory=dict)
    knownSubtypeSlugs: list[str] = Field(default_factory=list)
    sampleUniqueLabels: list[str] = Field(default_factory=list)
    parseStatus: Literal["ok", "warning"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)




class UniqueGloveMod(StrictBaseModel):
    id: str
    text: str


class UniqueItem(StrictBaseModel):
    id: str
    slug: str
    source: Literal["poe2db"]
    sourceUrl: str
    kind: str
    name: str
    baseType: str | None = None
    itemClass: str = "Gloves"
    rarity: Literal["Unique"] = "Unique"
    icon: str | None = None
    requirements: dict[str, int | None] = Field(default_factory=dict)
    defences: dict[str, Any] = Field(default_factory=dict)
    implicitMods: list[UniqueGloveMod] = Field(default_factory=list)
    explicitMods: list[UniqueGloveMod] = Field(default_factory=list)
    flavourText: list[str] = Field(default_factory=list)
    tooltipSections: list[TooltipSection] = Field(default_factory=list)
    parseStatus: Literal["ok", "warning"] = "ok"
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


# Backwards-compatible name retained while legacy uniqueGloves/Boots/Helmets
# payload fields are deprecated in favour of uniqueItems.
UniqueGlove = UniqueItem

class ModifierSourceMechanic(StrictBaseModel):
    id: str
    label: str
    order: int


class DataSnapshot(StrictBaseModel):
    id: str
    sourceUrl: str
    snapshotPath: str
    fromCache: bool


class ParserSanityReport(StrictBaseModel):
    loadedGloveBases: int = 0
    loadedBootBases: int = 0
    loadedHelmetBases: int = 0
    discoveredUniqueGloves: int = 0
    importedUniqueGloves: int = 0
    importedUniqueBoots: int = 0
    discoveredUniqueHelmets: int = 0
    importedUniqueHelmets: int = 0
    uniqueHelmetsWithoutExplicitMods: int = 0
    uniqueGlovesWithoutExplicitMods: int = 0
    uniqueGlovesWithoutSourceUrl: int = 0
    uniqueGlovesWithFlavourText: int = 0
    uniqueBootsWithFlavourText: int = 0
    uniqueBootsWithoutFlavourText: int = 0
    uniqueHelmetsWithFlavourText: int = 0
    uniqueItemsWithFlavourText: int = 0
    uniqueItemsWithoutFlavourText: int = 0
    importedUniqueItems: int = 0
    importedUniqueItemClasses: int = 0
    uniqueItemsByClass: dict[str, int] = Field(default_factory=dict)
    weaponUniqueItemsByClass: dict[str, int] = Field(default_factory=dict)
    importedWeaponUniqueItems: int = 0
    importedWeaponUniqueItemClasses: int = 0
    importedBaseItems: int = 0
    importedBaseItemClasses: int = 0
    baseItemsByClass: dict[str, int] = Field(default_factory=dict)
    deprecatedUniquePayloadFields: list[str] = Field(default_factory=list)
    loadedAugments: int = 0
    loadedRuneAugments: int = 0
    expectedRuneAugments: int = 42
    discoveredRuneAugments: int = 0
    importedRuneAugments: int = 0
    importedRuneAugmentsWithNormalEffects: int = 0
    importedRuneAugmentsWithAllNormalConditions: int = 0
    importedRuneAugmentsWithBondedEffects: int = 0
    importedRuneAugmentsWithIcons: int = 0
    importedRuneAugmentsWithRequirements: int = 0
    augmentIndexWarnings: list[str] = Field(default_factory=list)
    augmentCoverage: dict[str, Any] = Field(default_factory=dict)
    augmentIndexAudit: dict[str, Any] = Field(default_factory=dict)
    loadedSocketAugments: int = 0
    socketAugmentWarnings: list[dict[str, Any]] = Field(default_factory=list)
    loadedAugmentCatalogueEntries: int = 0
    augmentCatalogueSocketCandidates: int = 0
    augmentCatalogueDetailLoaded: int = 0
    augmentCatalogueDetailFailed: int = 0
    augmentCatalogueIndexOnly: int = 0
    augmentCatalogueEntriesWithEffects: int = 0
    augmentCatalogueBySection: dict[str, int] = Field(default_factory=dict)
    augmentCatalogueByCategory: dict[str, int] = Field(default_factory=dict)
    augmentCatalogueDetailStatusCounts: dict[str, int] = Field(default_factory=dict)
    augmentCatalogueDetailSourceCounts: dict[str, int] = Field(default_factory=dict)
    augmentSocketCandidateAudit: dict[str, Any] = Field(default_factory=dict)
    loadedEditorModifierPools: int = 0
    loadedBootEditorModifierPools: int = 0
    loadedBootNormalExplicitPools: int = 0
    loadedBodyArmourEditorModifierPools: int = 0
    loadedBodyArmourNormalExplicitPools: int = 0
    loadedHelmetEditorModifierPools: int = 0
    loadedHelmetNormalExplicitPools: int = 0
    loadedRingEditorModifierPools: int = 0
    loadedRingNormalExplicitPools: int = 0
    loadedAmuletEditorModifierPools: int = 0
    loadedAmuletNormalExplicitPools: int = 0
    loadedBeltEditorModifierPools: int = 0
    loadedBeltNormalExplicitPools: int = 0
    loadedShieldEditorModifierPools: int = 0
    loadedShieldNormalExplicitPools: int = 0
    loadedFocusEditorModifierPools: int = 0
    loadedFocusNormalExplicitPools: int = 0
    loadedQuiverEditorModifierPools: int = 0
    loadedQuiverNormalExplicitPools: int = 0


class PlannerPocData(StrictBaseModel):
    schemaVersion: Literal["poc-0.21"]
    parserVersion: str
    generatedAt: str
    source: Literal["poe2db"]
    sourceUrls: list[str]
    items: list[PlannerItem]
    augment: PlannerAugment
    augments: list[PlannerAugment] = Field(default_factory=list)
    augmentCatalogue: AugmentCatalogue | None = None
    itemClasses: list[ItemClassSummary] = Field(default_factory=list)
    itemSubtypes: list[ItemSubtype] = Field(default_factory=list)
    normalExplicitPools: list[NormalExplicitPool] = Field(default_factory=list)
    editorModifierPools: list[EditorModifierPool] = Field(default_factory=list)
    modifierSourceMechanics: list[ModifierSourceMechanic] = Field(default_factory=list)
    modifierAudits: list[dict[str, Any]] = Field(default_factory=list)
    baseItems: list[BaseItem] = Field(default_factory=list)
    uniqueItems: list[UniqueItem] = Field(default_factory=list)
    uniqueGloves: list[UniqueItem] = Field(default_factory=list)
    uniqueBoots: list[UniqueItem] = Field(default_factory=list)
    uniqueHelmets: list[UniqueItem] = Field(default_factory=list)
    dataSnapshots: list[DataSnapshot] = Field(default_factory=list)
    parserSanity: ParserSanityReport = Field(default_factory=ParserSanityReport)
    payloadHealth: dict[str, Any] = Field(default_factory=dict)


def validate_ui_payload(payload: dict[str, Any]) -> PlannerPocData:
    return PlannerPocData.model_validate(payload)


def ui_payload_json_schema() -> dict[str, Any]:
    """Return the frontend/tooling JSON schema for the UI payload.

    Keep runtime validation on Pydantic, but export the full model schema instead
    of a shallow hand-written object. This makes accidental UI-contract drift
    visible to frontend tooling and generated types.
    """
    schema = PlannerPocData.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "PoE2DB Planner POC Data"
    return schema
