import { useMemo } from "react";
import type { EditorModifier, PlannerAugment } from "../../../../types";
import {
  augmentConditionForItemClass,
  createAugmentLookupIndex,
  normalizeAugmentCondition,
  resolveAppliedAugmentEffectsForItem,
} from "../../domain/augmentEffects";

const PREVIEW_ITEM_CLASSES = [
  { itemClass: "Bows", label: "Bow / Martial Weapon" },
  { itemClass: "Wands", label: "Wand" },
  { itemClass: "Staves", label: "Staff" },
  { itemClass: "Body Armours", label: "Body Armour" },
  { itemClass: "Shields", label: "Shield" },
  { itemClass: "Quivers", label: "Unknown target + All Equipment fallback" },
];

function normalEffects(augment: PlannerAugment) {
  return augment.augmentEffects.filter((effect) => !effect.bonded);
}

function firstAugmentForCondition(
  augments: PlannerAugment[],
  condition: string | null,
): PlannerAugment | null {
  if (!condition) {
    return (
      augments.find((augment) =>
        normalEffects(augment).some(
          (effect) => normalizeAugmentCondition(effect.condition) === "all_equipment",
        ),
      ) ?? null
    );
  }

  return (
    augments.find((augment) =>
      normalEffects(augment).some(
        (effect) => normalizeAugmentCondition(effect.condition) === condition,
      ),
    ) ?? null
  );
}

function syntheticSocketMod(augment: PlannerAugment): EditorModifier {
  return {
    id: `debug-applied-augment:${augment.id}`,
    text: `Fallback socket text for ${augment.name}`,
    textTemplate: null,
    displayRangeText: null,
    pickerLabel: null,
    runeName: augment.name,
    socketStatText: `Fallback socket text for ${augment.name}`,
    fixedValue: true,
    editableValues: [],
    sourceGroup: "debug-applied-augment",
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
    sourceUrl: augment.sourceUrl,
  };
}

export function AppliedAugmentPreviewPanel({
  augments,
}: {
  augments: PlannerAugment[];
}) {
  const augmentIndex = useMemo(() => createAugmentLookupIndex(augments), [augments]);

  if (!augments.length) return null;

  const rows = PREVIEW_ITEM_CLASSES.map(({ itemClass, label }) => {
    const itemCondition = augmentConditionForItemClass(itemClass);
    const augment = firstAugmentForCondition(augments, itemCondition);
    const resolved = augment
      ? resolveAppliedAugmentEffectsForItem({
          itemClass,
          socketMods: [syntheticSocketMod(augment)],
          lookup: augmentIndex,
        })[0]
      : null;

    return {
      itemClass,
      label,
      itemCondition: itemCondition ?? "all_equipment fallback",
      augment,
      resolved,
    };
  });

  return (
    <section className="applied-augment-preview-panel">
      <header>
        <h2>Applied rune stat preview</h2>
        <p>
          Representative checks for the same resolver used by the item tooltip.
          Bonded effects are intentionally excluded here.
        </p>
      </header>
      <div className="applied-augment-preview-table-wrap">
        <table className="applied-augment-preview-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Item condition</th>
              <th>Sample rune</th>
              <th>Resolved effect</th>
              <th>Resolved condition</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.itemClass}>
                <td>{row.label}</td>
                <td><code>{row.itemCondition}</code></td>
                <td>{row.augment?.name ?? "—"}</td>
                <td>{row.resolved?.text ?? "No matching sample augment"}</td>
                <td><code>{row.resolved?.condition ?? "—"}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
