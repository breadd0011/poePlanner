import { strict as assert } from "node:assert";

import { calculateDefenceRange } from "../src/features/equipment-planner/domain/itemDefences.ts";
import {
  augmentConditionForItemClass,
  normalizeAugmentCondition,
  resolveAppliedAugmentEffectsForItem,
  resolveSocketAugmentsForMods,
} from "../src/features/equipment-planner/domain/augmentEffects.ts";
import {
  adjustedItemProperties,
  calculatePercentScaledValue,
  calculatePhysicalDamageRange,
} from "../src/features/equipment-planner/domain/itemProperties.ts";
import {
  computeSocketCapacity,
  corruptedAfterModifierSelection,
  corruptedAfterSocketCountChange,
  sanitizeSelectionIdsForCorruptionState,
  socketCountAfterCorruptedChange,
  trimSocketSelectionIds,
} from "../src/features/equipment-planner/domain/itemSockets.ts";

function defence(base, flatMin, flatMax, incMin, incMax, quality) {
  return calculateDefenceRange({
    base,
    flat: { min: flatMin, max: flatMax },
    percent: { min: incMin, max: incMax },
    quality,
  });
}


function augmentEffect(condition, text, bonded = false, label = null) {
  return { condition, label, bonded, text };
}

function augment(name, effects) {
  return {
    id: `augment:${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
    slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
    source: "poe2db",
    sourceUrl: `https://example.test/${name}`,
    name,
    baseType: null,
    itemClass: "Augment",
    icon: null,
    tooltipSections: [],
    parseStatus: "ok",
    warnings: [],
    diagnostics: [],
    kind: "augment",
    augmentEffects: effects,
  };
}

function socketMod(id, runeName, fallbackText = "fallback socket stat") {
  return {
    id,
    text: fallbackText,
    textTemplate: null,
    displayRangeText: null,
    pickerLabel: null,
    runeName,
    socketStatText: fallbackText,
    fixedValue: true,
    editableValues: [],
    sourceGroup: "golden",
    sourceMechanic: "augment",
    affixType: "prefix",
    family: null,
    generationGroup: null,
    weightRaw: null,
    weightPercent: null,
    level: null,
    tierCount: null,
    detailStatus: "available",
    tags: [],
    keywords: [],
    sourceUrl: "https://example.test/mod",
  };
}

const desertRune = augment("Desert Rune", [
  augmentEffect("martial_weapon", "Adds 7 to 11 Fire Damage", false, "Martial Weapon"),
  augmentEffect("wand_or_staff", "Gain 8% of Damage as Extra Fire Damage", false, "Wand or Staff"),
  augmentEffect("armour", "+12% to Fire Resistance", false, "Armour"),
  augmentEffect("martial_weapon", "25% increased Ignite Magnitude", true, "Martial Weapon"),
]);

const allEquipmentRune = augment("Omen Rune", [
  augmentEffect("All Equipment", "+5 to all Attributes", false, "All Equipment"),
]);

const goldenAugmentConditionCases = [
  { name: "Bows use martial weapon effects", itemClass: "Bows", expected: "martial_weapon" },
  { name: "Crossbows use martial weapon effects", itemClass: "Crossbows", expected: "martial_weapon" },
  { name: "Wands use wand or staff effects", itemClass: "Wands", expected: "wand_or_staff" },
  { name: "Staves use wand or staff effects", itemClass: "Staves", expected: "wand_or_staff" },
  { name: "Body Armours use armour effects", itemClass: "Body Armours", expected: "armour" },
  { name: "Shields use armour effects", itemClass: "Shields", expected: "armour" },
  { name: "Quivers are not augment-effect targets", itemClass: "Quivers", expected: null },
];

const goldenAugmentConditionNormalizationCases = [
  { name: "label-style martial condition normalizes", value: "Martial Weapon", expected: "martial_weapon" },
  { name: "label-style wand/staff condition normalizes", value: "Wand or Staff", expected: "wand_or_staff" },
  { name: "label-style all equipment condition normalizes", value: "All Equipment", expected: "all_equipment" },
];

const goldenAppliedAugmentCases = [
  {
    name: "bow selects martial weapon rune effect",
    itemClass: "Bows",
    augments: [desertRune],
    socketMods: [socketMod("desert-bow", "Desert Rune")],
    expectedText: ["Adds 7 to 11 Fire Damage"],
    expectedConditions: ["martial_weapon"],
  },
  {
    name: "wand selects wand-or-staff rune effect",
    itemClass: "Wands",
    augments: [desertRune],
    socketMods: [socketMod("desert-wand", "Desert Rune")],
    expectedText: ["Gain 8% of Damage as Extra Fire Damage"],
    expectedConditions: ["wand_or_staff"],
  },
  {
    name: "armour selects armour rune effect",
    itemClass: "Body Armours",
    augments: [desertRune],
    socketMods: [socketMod("desert-armour", "Desert Rune")],
    expectedText: ["+12% to Fire Resistance"],
    expectedConditions: ["armour"],
  },
  {
    name: "all-equipment effect is fallback for unknown augment target class",
    itemClass: "Quivers",
    augments: [allEquipmentRune],
    socketMods: [socketMod("omen-quiver", "Omen Rune")],
    expectedText: ["+5 to all Attributes"],
    expectedConditions: ["all_equipment"],
  },
  {
    name: "specific item-class effect beats all-equipment fallback",
    itemClass: "Bows",
    augments: [
      augment("Hybrid Rune", [
        augmentEffect("All Equipment", "+5 to all Attributes", false, "All Equipment"),
        augmentEffect("Martial Weapon", "Adds 2 to 4 Physical Damage", false, "Martial Weapon"),
      ]),
    ],
    socketMods: [socketMod("hybrid-bow", "Hybrid Rune")],
    expectedText: ["Adds 2 to 4 Physical Damage"],
    expectedConditions: ["martial_weapon"],
  },

  {
    name: "multiple socketed runes preserve selected socket order",
    itemClass: "Bows",
    augments: [
      desertRune,
      augment("Storm Rune", [
        augmentEffect("Martial Weapon", "Adds 1 to 20 Lightning Damage", false, "Martial Weapon"),
        augmentEffect("Armour", "+12% to Lightning Resistance", false, "Armour"),
      ]),
    ],
    socketMods: [
      socketMod("storm-first", "Storm Rune"),
      socketMod("desert-second", "Desert Rune"),
    ],
    expectedText: ["Adds 1 to 20 Lightning Damage", "Adds 7 to 11 Fire Damage"],
    expectedConditions: ["martial_weapon", "martial_weapon"],
  },
  {
    name: "duplicate socketed runes resolve duplicate applied lines",
    itemClass: "Bows",
    augments: [desertRune],
    socketMods: [
      socketMod("desert-duplicate", "Desert Rune"),
      socketMod("desert-duplicate", "Desert Rune"),
    ],
    expectedText: ["Adds 7 to 11 Fire Damage", "Adds 7 to 11 Fire Damage"],
    expectedConditions: ["martial_weapon", "martial_weapon"],
  },
  {
    name: "missing augment registry falls back to socket stat text",
    itemClass: "Bows",
    augments: [],
    socketMods: [socketMod("missing-registry", "Missing Rune", "fallback socket stat")],
    expectedText: ["fallback socket stat"],
    expectedConditions: ["martial_weapon"],
  },
];


const goldenSocketAugmentCases = [
  {
    name: "socket augment registry preserves order for multiple sockets",
    socketMods: [
      socketMod("storm-first", "Storm Rune"),
      socketMod("desert-second", "Desert Rune"),
    ],
    augments: [
      desertRune,
      augment("Storm Rune", [
        augmentEffect("Martial Weapon", "Adds 1 to 20 Lightning Damage", false, "Martial Weapon"),
      ]),
    ],
    expectedNames: ["Storm Rune", "Desert Rune"],
  },
  {
    name: "socket augment registry preserves duplicate rune slots",
    socketMods: [
      socketMod("desert-duplicate", "Desert Rune"),
      socketMod("desert-duplicate", "Desert Rune"),
    ],
    augments: [desertRune],
    expectedNames: ["Desert Rune", "Desert Rune"],
  },
  {
    name: "socket augment registry keeps unknown socket slots as empty tooltip data",
    socketMods: [
      socketMod("unknown-rune", "Unknown Rune"),
      socketMod("desert-known", "Desert Rune"),
    ],
    augments: [desertRune],
    expectedNames: [null, "Desert Rune"],
  },
  {
    name: "socket augment registry resolves generalized augmentName fields",
    socketMods: [
      { ...socketMod("soul-core", null), augmentName: "Soul Core of Tacati", runeName: null, augmentCategory: "soul_core" },
    ],
    augments: [
      augment("Soul Core of Tacati", [
        augmentEffect("Armour", "+11% to Chaos Resistance", false, "Armour"),
      ]),
    ],
    expectedNames: ["Soul Core of Tacati"],
  },
];

const goldenDefenceCases = [
  {
    name: "quality only armour",
    args: [100, 0, 0, 0, 0, 20],
    expected: { min: 120, max: 120 },
  },
  {
    name: "flat armour before quality",
    args: [100, 35, 35, 0, 0, 20],
    expected: { min: 162, max: 162 },
  },
  {
    name: "increased armour before quality",
    args: [100, 0, 0, 60, 60, 20],
    expected: { min: 192, max: 192 },
  },
  {
    name: "flat plus increased plus quality range",
    args: [120, 30, 50, 60, 100, 20],
    expected: { min: 288, max: 408 },
  },
  {
    name: "socket rune fixed increased defences",
    args: [100, 0, 0, 14, 14, 0],
    expected: { min: 114, max: 114 },
  },
];

for (const testCase of goldenDefenceCases) {
  assert.deepEqual(defence(...testCase.args), testCase.expected, testCase.name);
}

function editable(index, min, max) {
  return {
    index,
    min,
    max,
    value: null,
    rangeText: null,
    valuePrefix: "",
    valueSuffix: "",
  };
}

function mod(id, text, ranges = []) {
  return {
    id,
    text,
    displayRangeText: null,
    editableValues: ranges,
    sourceGroup: "golden",
    sourceMechanic: "normal",
    affixType: "prefix",
    family: null,
    generationGroup: null,
    weightRaw: null,
    weightPercent: null,
    level: null,
    tierCount: null,
    detailStatus: "available",
    tags: [],
    keywords: [],
    sourceUrl: "",
  };
}

function propertyValues(lines) {
  return Object.fromEntries(lines.map((line) => [line.key, line.value]));
}

const goldenItemPropertyFormulaCases = [
  {
    name: "physical damage applies flat then increased then quality",
    actual: calculatePhysicalDamageRange({
      base: { min: 10, max: 20 },
      flat: { min: 5, max: 10 },
      percent: { min: 100, max: 100 },
      quality: 20,
    }),
    expected: { min: 36, max: 72 },
  },
  {
    name: "percent scaled weapon property keeps decimals",
    actual: calculatePercentScaledValue({
      base: 1.5,
      percent: { min: 10, max: 20 },
      decimals: 2,
    }),
    expected: { min: 1.65, max: 1.8 },
  },
];

const goldenItemPropertyCases = [
  {
    name: "weapon properties include local physical, elemental, attack speed, and crit",
    base: {
      name: "Golden Sword",
      requirements: {},
      defences: {},
      properties: {
        physicalDamage: { min: 10, max: 20 },
        criticalHitChance: 5,
        attacksPerSecond: 1.5,
        weaponRange: 1.1,
      },
      propertyLines: [
        "Physical Damage: 10-20",
        "Critical Hit Chance: 5%",
        "Attacks per Second: 1.5",
        "Weapon Range: 1.1",
      ],
    },
    quality: 20,
    mods: [
      mod("flat-phys", "Adds # to # Physical Damage", [editable(0, 5, 5), editable(1, 10, 10)]),
      mod("inc-phys", "#% increased Physical Damage", [editable(0, 100, 100)]),
      mod("fire", "Adds # to # Fire Damage to Attacks", [editable(0, 1, 1), editable(1, 3, 3)]),
      mod("speed", "#% increased Attack Speed", [editable(0, 20, 20)]),
      mod("crit", "#% increased Critical Hit Chance", [editable(0, 50, 50)]),
    ],
    expected: {
      physicalDamage: "36-72",
      fireDamage: "1-3",
      criticalHitChance: "7.5%",
      attacksPerSecond: "1.8",
      weaponRange: "1.1",
    },
  },

  {
    name: "global character stats do not change local item properties",
    base: {
      name: "Golden Bow",
      requirements: {},
      defences: {},
      properties: {
        physicalDamage: { min: 10, max: 20 },
        criticalHitChance: 5,
        attacksPerSecond: 1.5,
      },
      propertyLines: [
        "Physical Damage: 10-20",
        "Critical Hit Chance: 5%",
        "Attacks per Second: 1.5",
      ],
    },
    quality: 0,
    mods: [
      mod("global-phys", "#% increased Attack Skills Damage", [editable(0, 50, 50)]),
      mod("spell-added", "Adds # to # Fire Damage to Spells", [editable(0, 9, 9), editable(1, 13, 13)]),
      mod("global-crit", "#% increased Global Critical Hit Chance", [editable(0, 100, 100)]),
      mod("life", "+# to maximum Life", [editable(0, 80, 80)]),
    ],
    expected: {
      physicalDamage: "10-20",
      criticalHitChance: "5%",
      attacksPerSecond: "1.5",
    },
  },
  {
    name: "explicit enchant and socket style local mods combine on item properties",
    base: {
      name: "Golden Axe",
      requirements: {},
      defences: {},
      properties: {
        physicalDamage: { min: 20, max: 40 },
        attacksPerSecond: 1.2,
      },
      propertyLines: ["Physical Damage: 20-40", "Attacks per Second: 1.2"],
    },
    quality: 23,
    mods: [
      mod("explicit-flat", "Adds # to # Physical Damage", [editable(0, 4, 4), editable(1, 8, 8)]),
      mod("enchant-inc", "#% increased Physical Damage", [editable(0, 50, 50)]),
      mod("socket-speed", "#% increased Attack Speed", [editable(0, 10, 10)]),
    ],
    expected: {
      physicalDamage: "44-88",
      attacksPerSecond: "1.32",
    },
  },
  {
    name: "sceptre spirit and shield block chance are calculated from base properties",
    base: {
      name: "Golden Shield Sceptre",
      requirements: {},
      defences: {},
      properties: { spirit: 100, block_chance: "25%" },
      propertyLines: ["Spirit: 100", "Block chance: 25%"],
    },
    quality: 0,
    mods: [
      mod("spirit", "# to Spirit", [editable(0, 15, 25)]),
      mod("block", "+#% to Block chance", [editable(0, 5, 5)]),
    ],
    expected: {
      spirit: "115 - 125",
      blockChance: "30%",
    },
  },
];

for (const testCase of goldenItemPropertyFormulaCases) {
  assert.deepEqual(testCase.actual, testCase.expected, testCase.name);
}

for (const testCase of goldenItemPropertyCases) {
  assert.deepEqual(
    propertyValues(
      adjustedItemProperties(
        testCase.base,
        testCase.quality,
        testCase.mods,
        [],
        {},
      ),
    ),
    testCase.expected,
    testCase.name,
  );
}

function uniqueWithHiddenSockets(hiddenSockets) {
  return hiddenSockets === null
    ? null
    : {
        explicitMods: [
          {
            id: `unique-hidden-sockets-${hiddenSockets}`,
            text: `Has ${hiddenSockets} Augment Sockets`,
          },
        ],
      };
}

function capacity({ itemClass, selectedSocketCount = 2, hiddenSockets = null }) {
  return computeSocketCapacity({
    itemClass,
    selectedUnique: uniqueWithHiddenSockets(hiddenSockets),
    selectedSocketCount,
  });
}

function selectedIdsAfterSocketCountChange(selectedMods, nextSocketCount) {
  return trimSocketSelectionIds(
    selectedMods.map((mod) => mod.id),
    selectedMods,
    nextSocketCount,
  );
}

function selectedIdsAfterCorruptedChange(selectedMods, nextCorrupted) {
  return sanitizeSelectionIdsForCorruptionState({
    selectedIds: selectedMods.map((mod) => mod.id),
    allMods: selectedMods,
    nextCorrupted,
    socketCapacity: socketCountAfterCorruptedChange(3, nextCorrupted),
  });
}

const goldenSocketCases = [
  {
    name: "gloves manual socket selector defaults to two",
    args: { itemClass: "Gloves" },
    expected: 2,
  },
  {
    name: "boots manual socket selector can be one",
    args: { itemClass: "Boots", selectedSocketCount: 1 },
    expected: 1,
  },
  {
    name: "boots manual socket selector can be three",
    args: { itemClass: "Boots", selectedSocketCount: 3 },
    expected: 3,
  },
  {
    name: "unique hidden sockets override manual selector up to grid size",
    args: { itemClass: "Boots", selectedSocketCount: 2, hiddenSockets: 4 },
    expected: 4,
  },
  {
    name: "six-socket unique body armour is no longer capped to four",
    args: { itemClass: "Body Armours", selectedSocketCount: 2, hiddenSockets: 6 },
    expected: 6,
  },
];

const goldenCorruptionCases = [
  {
    name: "choosing three sockets forces corrupted on",
    args: [false, 3],
    expected: true,
  },
  {
    name: "lowering sockets to two does not clear corrupted",
    args: [true, 2],
    expected: true,
  },
  {
    name: "lowering sockets to one does not clear corrupted",
    args: [true, 1],
    expected: true,
  },
  {
    name: "choosing two sockets does not force corrupted on",
    args: [false, 2],
    expected: false,
  },
  {
    name: "selecting augment socket mod does not force corrupted on",
    modArgs: [false, "augment"],
    expected: false,
  },
  {
    name: "selecting corruption enchant forces corrupted on",
    modArgs: [false, "corrupted"],
    expected: true,
  },
];

const goldenCorruptedToggleCases = [
  {
    name: "turning corrupted off clamps three sockets to two",
    args: [3, false],
    expected: 2,
  },
  {
    name: "turning corrupted off keeps two sockets at two",
    args: [2, false],
    expected: 2,
  },
  {
    name: "turning corrupted on does not change socket count",
    args: [1, true],
    expected: 1,
  },
];

const goldenCorruptedSelectionCases = [
  {
    name: "non-corrupted state removes corruption enchantments and clamps third socket augment",
    args: [
      [
        { id: "normal-armour", sourceMechanic: "normal" },
        { id: "vaal-armour", sourceMechanic: "corrupted" },
        { id: "rune-armour-1", sourceMechanic: "augment" },
        { id: "rune-armour-2", sourceMechanic: "augment" },
        { id: "rune-armour-3", sourceMechanic: "augment" },
      ],
      false,
    ],
    expected: ["normal-armour", "rune-armour-1", "rune-armour-2"],
  },
  {
    name: "turning corrupted off removes corruption enchantments and trims third socket selection",
    args: [
      [
        { id: "normal-armour", sourceMechanic: "normal" },
        { id: "vaal-armour", sourceMechanic: "corrupted" },
        { id: "rune-armour-1", sourceMechanic: "augment" },
        { id: "rune-armour-2", sourceMechanic: "augment" },
        { id: "rune-armour-3", sourceMechanic: "augment" },
      ],
      false,
    ],
    expected: ["normal-armour", "rune-armour-1", "rune-armour-2"],
  },
  {
    name: "turning corrupted on preserves selections",
    args: [[{ id: "vaal-armour", sourceMechanic: "corrupted" }], true],
    expected: ["vaal-armour"],
  },
];

const goldenSocketSelectionCases = [
  {
    name: "lowering socket count from three to two removes third socket augment",
    args: [
      [
        { id: "normal-armour", sourceMechanic: "normal" },
        { id: "rune-armour-1", sourceMechanic: "augment" },
        { id: "rune-armour-2", sourceMechanic: "augment" },
        { id: "rune-armour-3", sourceMechanic: "augment" },
      ],
      2,
    ],
    expected: ["normal-armour", "rune-armour-1", "rune-armour-2"],
  },
  {
    name: "lowering socket count from three to one removes second and third socket augments",
    args: [
      [
        { id: "rune-armour-1", sourceMechanic: "augment" },
        { id: "rune-armour-2", sourceMechanic: "augment" },
        { id: "rune-armour-3", sourceMechanic: "augment" },
      ],
      1,
    ],
    expected: ["rune-armour-1"],
  },
];

for (const testCase of goldenAugmentConditionCases) {
  assert.equal(
    augmentConditionForItemClass(testCase.itemClass),
    testCase.expected,
    testCase.name,
  );
}

for (const testCase of goldenAugmentConditionNormalizationCases) {
  assert.equal(
    normalizeAugmentCondition(testCase.value),
    testCase.expected,
    testCase.name,
  );
}

for (const testCase of goldenAppliedAugmentCases) {
  const resolved = resolveAppliedAugmentEffectsForItem({
    itemClass: testCase.itemClass,
    socketMods: testCase.socketMods,
    augments: testCase.augments,
  });
  assert.deepEqual(
    resolved.map((line) => line.text),
    testCase.expectedText,
    testCase.name,
  );
  assert.deepEqual(
    resolved.map((line) => line.condition),
    testCase.expectedConditions,
    `${testCase.name} condition`,
  );
}


for (const testCase of goldenSocketAugmentCases) {
  const resolved = resolveSocketAugmentsForMods(testCase.socketMods, testCase.augments);
  assert.deepEqual(
    resolved.map((augment) => augment?.name ?? null),
    testCase.expectedNames,
    testCase.name,
  );
}

for (const testCase of goldenSocketCases) {
  assert.equal(capacity(testCase.args), testCase.expected, testCase.name);
}

for (const testCase of goldenCorruptionCases) {
  if (testCase.args) {
    assert.equal(
      corruptedAfterSocketCountChange(...testCase.args),
      testCase.expected,
      testCase.name,
    );
  } else {
    assert.equal(
      corruptedAfterModifierSelection(...testCase.modArgs),
      testCase.expected,
      testCase.name,
    );
  }
}

for (const testCase of goldenCorruptedToggleCases) {
  assert.equal(
    socketCountAfterCorruptedChange(...testCase.args),
    testCase.expected,
    testCase.name,
  );
}

for (const testCase of goldenCorruptedSelectionCases) {
  assert.deepEqual(
    selectedIdsAfterCorruptedChange(...testCase.args),
    testCase.expected,
    testCase.name,
  );
}

for (const testCase of goldenSocketSelectionCases) {
  assert.deepEqual(
    selectedIdsAfterSocketCountChange(...testCase.args),
    testCase.expected,
    testCase.name,
  );
}

console.log(
  `golden planner regressions passed (${goldenDefenceCases.length + goldenItemPropertyFormulaCases.length + goldenItemPropertyCases.length + goldenSocketCases.length + goldenCorruptionCases.length + goldenCorruptedToggleCases.length + goldenCorruptedSelectionCases.length + goldenSocketSelectionCases.length + goldenAugmentConditionCases.length + goldenAugmentConditionNormalizationCases.length + goldenAppliedAugmentCases.length + goldenSocketAugmentCases.length} cases)`,
);
