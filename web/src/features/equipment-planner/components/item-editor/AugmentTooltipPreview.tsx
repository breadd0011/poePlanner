import type { PlannerAugment, TooltipSection } from "../../../../types";
import { iconToWebPath, lc, renderPoeText, TooltipSeparator } from "./itemPresentation";

type AugmentTooltipPreviewProps = {
  augment: PlannerAugment;
  compact?: boolean;
};

const CONDITION_LABELS: Record<string, string> = {
  martial_weapon: "Martial Weapon",
  wand_or_staff: "Wand or Staff",
  armour: "Armour",
  all_equipment: "All Equipment",
};

function labelForCondition(condition: string, fallback?: string | null) {
  return fallback || CONDITION_LABELS[condition] || condition;
}

function sectionLines(sections: TooltipSection[], kind: TooltipSection["kind"]) {
  return sections
    .filter((section) => section.kind === kind)
    .flatMap((section) => section.lines);
}

function uniqueLines(lines: string[]) {
  return Array.from(new Set(lines.map((line) => line.trim()).filter(Boolean)));
}

function displayPropertyLines(lines: string[]) {
  return uniqueLines(lines).filter((line) => {
    if (!/^Stack Size:/i.test(line)) return true;
    return /^Stack Size:\s*\S/i.test(line);
  });
}

function requirementText(line: string) {
  return line.replace(/^Requires:\s*/i, "").trim();
}

export function AugmentTooltipPreview({
  augment,
  compact = false,
}: AugmentTooltipPreviewProps) {
  const iconPath = iconToWebPath(augment.icon);
  const propertyLines = displayPropertyLines(sectionLines(augment.tooltipSections, "property"));
  const requirementLines = uniqueLines(sectionLines(augment.tooltipSections, "requirement").map(requirementText));
  const descriptionLines = uniqueLines(sectionLines(augment.tooltipSections, "description"));
  const normalEffects = augment.augmentEffects.filter((effect) => !effect.bonded);
  const bondedEffects = augment.augmentEffects.filter((effect) => effect.bonded);

  return (
    <div
      className={
        compact
          ? "item-card planner-item-card poe2-itemPopup poe2-normalPopup item-tooltip-preview augment-tooltip-preview augment-tooltip-preview--compact"
          : "item-card planner-item-card poe2-itemPopup poe2-normalPopup item-tooltip-preview augment-tooltip-preview"
      }
    >
      <div className="poe2-itemHeader singleLine">
        <div className="poe2-itemName poe2-typeLine">{lc(augment.name)}</div>
      </div>
      <div className="poe2-content">
        <div className="poe2-displayProperty">{lc(augment.itemClass || "Augment")}</div>
        {propertyLines.map((line) => (
          <div className="poe2-displayProperty" key={`property:${line}`}>
            {lc(renderPoeText(line))}
          </div>
        ))}

        {requirementLines.length ? (
          <>
            <TooltipSeparator />
            <div className="poe2-requirements">
              {lc(
                <>
                  Requires: <span className="poe2-colourDefault">{requirementLines.join(", ")}</span>
                </>,
              )}
            </div>
          </>
        ) : null}

        {normalEffects.length ? (
          <>
            <TooltipSeparator />
            {normalEffects.map((effect) => (
              <div className="poe2-implicitMod" key={`normal:${effect.condition}:${effect.text}`}>
                {lc(
                  <>
                    {labelForCondition(effect.condition, effect.label)}: {renderPoeText(effect.text)}
                  </>,
                )}
              </div>
            ))}
          </>
        ) : null}

        {bondedEffects.length ? (
          <>
            <TooltipSeparator />
            <div className="poe2-bondedMod">{lc("Bonded:")}</div>
            {bondedEffects.map((effect) => (
              <div className="poe2-bondedMod" key={`bonded:${effect.condition}:${effect.text}`}>
                {lc(
                  <>
                    {labelForCondition(effect.condition, effect.label)}: {renderPoeText(effect.text)}
                  </>,
                )}
              </div>
            ))}
          </>
        ) : null}

        {descriptionLines.length ? (
          <>
            <TooltipSeparator />
            {descriptionLines.map((line, index) => (
              <div className="poe2-defaultText" key={`description:${index}:${line}`}>
                {lc(renderPoeText(line))}
              </div>
            ))}
          </>
        ) : null}

        {iconPath ? (
          <div className="poe2-itemboximage">
            <img className="augment-tooltip-preview__icon" alt="" src={iconPath} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
