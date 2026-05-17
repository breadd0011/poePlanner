import type { EditorModifier, ItemModifierLine, PlannerAugment, UniqueItem } from "../../../../types";
import type { Rarity } from "../../domain/equipment";
import type { AppliedAugmentEffectLine } from "../../domain/augmentEffects";
import { formatDefenceValue, type DefenceRange } from "../../domain/itemDefences";
import type { CalculatedItemPropertyLine } from "../../domain/itemProperties";
import type { CustomValueState } from "../../domain/itemText";
import {
  FlavourTextLines,
  TooltipModLines,
  UniqueLineGroup,
} from "./TooltipPreviewParts";
import { SocketedItemArtwork } from "./SocketedItemPreview";
import {
  JoinedRequirementLine,
  lc,
  rarityPopupClass,
  renderPoeText,
  TooltipSeparator,
} from "./itemPresentation";

type SelectedModifierBuckets = {
  enchant: EditorModifier[];
  explicit: EditorModifier[];
  sockets: EditorModifier[];
};

type ItemTooltipPreviewProps = {
  customName: string;
  customValues: CustomValueState;
  defenceLines: DefenceRange[];
  displayName: string;
  iconPath: string | null;
  isCorrupted: boolean;
  isSanctified: boolean;
  itemLevel: number;
  propertyLines: CalculatedItemPropertyLine[];
  rarity: Rarity;
  requirementParts: string[];
  safeQuality: number;
  selectedBaseImplicitMods: ItemModifierLine[];
  selectedBaseName: string;
  selectedBuckets: SelectedModifierBuckets;
  selectedItemClass: string;
  selectedUnique: UniqueItem | null;
  socketCapacity: number;
  socketFilledCount: number;
  socketAugments: Array<PlannerAugment | null>;
  appliedSocketEffects: AppliedAugmentEffectLine[];
};

export function ItemTooltipPreview({
  customName,
  customValues,
  defenceLines,
  displayName,
  iconPath,
  isCorrupted,
  isSanctified,
  itemLevel,
  propertyLines,
  requirementParts,
  selectedBaseImplicitMods,
  selectedBaseName,
  selectedBuckets,
  selectedItemClass,
  selectedUnique,
  rarity,
  safeQuality,
  socketCapacity,
  socketFilledCount,
  socketAugments,
  appliedSocketEffects,
}: ItemTooltipPreviewProps) {
  const hasDoubleLineHeader = Boolean(selectedUnique || customName.trim());
  const previewSocketCapacity = Math.max(0, socketCapacity);
  const hasArtwork = Boolean(iconPath || previewSocketCapacity > 0);

  return (
    <div
      className={`item-card planner-item-card poe2-itemPopup ${rarityPopupClass(rarity)} item-tooltip-preview`}
    >
      <div
        className={
          hasDoubleLineHeader
            ? "poe2-itemHeader doubleLine"
            : "poe2-itemHeader singleLine"
        }
      >
        <div
          className={
            hasDoubleLineHeader ? "poe2-itemName" : "poe2-itemName poe2-typeLine"
          }
        >
          {lc(displayName)}
        </div>
        {hasDoubleLineHeader ? (
          <div className="poe2-itemName poe2-typeLine">
            {lc(selectedBaseName)}
          </div>
        ) : null}
      </div>
      <div className="poe2-content">
        <div className="poe2-displayProperty">
          {lc(
            <>
              {selectedItemClass}: Item Level{" "}
              <span className="poe2-colourDefault">{itemLevel}</span>
            </>,
          )}
        </div>
        {safeQuality > 0 ? (
          <div className="poe2-displayProperty">
            {lc(
              <>
                Quality: +
                <span className="poe2-colourAugmented">{safeQuality}</span>%
              </>,
            )}
          </div>
        ) : null}
        {propertyLines.map((line) => (
          <div className="poe2-displayProperty" key={`property:${line.key}`}>
            {lc(
              <>
                {line.label}:{" "}
                <span
                  className={
                    line.augmented
                      ? "poe2-colourAugmented"
                      : "poe2-colourDefault"
                  }
                >
                  {line.value}
                </span>
              </>,
            )}
          </div>
        ))}
        {defenceLines.map((line) => (
          <div className="poe2-displayProperty" key={line.key}>
            {lc(
              <>
                {line.label}:{" "}
                <span
                  className={
                    line.augmented
                      ? "poe2-colourAugmented"
                      : "poe2-colourDefault"
                  }
                >
                  {formatDefenceValue(line.min, line.max)}
                </span>
              </>,
            )}
          </div>
        ))}
        {requirementParts.length ? (
          <>
            <TooltipSeparator />
            <div className="poe2-requirements">
              {lc(<JoinedRequirementLine parts={requirementParts} />)}
            </div>
          </>
        ) : null}
        {appliedSocketEffects.length ? (
          <>
            <TooltipSeparator />
            {appliedSocketEffects.map((effect) => (
              <div className="poe2-socketMod" key={effect.id}>
                {lc(renderPoeText(effect.text))}
              </div>
            ))}
          </>
        ) : null}
        <TooltipModLines
          mods={selectedBuckets.enchant}
          customValues={customValues}
          className="poe2-enchantMod"
        />
        {selectedUnique?.implicitMods.length || selectedBaseImplicitMods.length ? (
          <UniqueLineGroup
            mods={
              selectedUnique?.implicitMods.length
                ? selectedUnique.implicitMods
                : selectedBaseImplicitMods
            }
            customValues={customValues}
            className="poe2-implicitMod"
          />
        ) : null}
        {selectedUnique?.explicitMods.length || selectedBuckets.explicit.length ? (
          <>
            <TooltipSeparator />
            {selectedUnique ? (
              <UniqueLineGroup
                mods={selectedUnique.explicitMods}
                customValues={customValues}
                className="poe2-explicitMod"
                withSeparator={false}
              />
            ) : null}
            <TooltipModLines
              mods={selectedBuckets.explicit}
              customValues={customValues}
              className="poe2-explicitMod"
              withSeparator={false}
            />
          </>
        ) : null}
        {isCorrupted || isSanctified ? (
          <>
            <TooltipSeparator />
            {isCorrupted ? <div className="poe2-unmet">{lc("Corrupted")}</div> : null}
            {isSanctified ? (
              <div className="poe2-cosmeticMod">{lc("Sanctified")}</div>
            ) : null}
          </>
        ) : null}
        {selectedUnique?.flavourText?.length ? (
          <FlavourTextLines lines={selectedUnique.flavourText} />
        ) : null}
        {hasArtwork ? (
          <div className="poe2-itemboximage">
            <SocketedItemArtwork
              className="item-tooltip-preview__artwork"
              iconPath={iconPath}
              label={displayName}
              socketCapacity={previewSocketCapacity}
              socketFilledCount={socketFilledCount}
              socketAugments={socketAugments}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
