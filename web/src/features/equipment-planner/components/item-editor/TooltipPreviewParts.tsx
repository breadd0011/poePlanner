import type { EditorModifier, UniqueItem } from "../../../../types";
import {
  type CustomValueState,
  renderModifierText,
  renderUniqueModText,
} from "../../domain/itemText";
import { lc, renderPoeText, TooltipSeparator } from "./itemPresentation";

export function UniqueLineGroup({
  mods,
  customValues,
  className,
  withSeparator = true,
}: {
  mods: UniqueItem["explicitMods"];
  customValues: CustomValueState;
  className: string;
  withSeparator?: boolean;
}) {
  if (!mods.length) return null;
  return (
    <>
      {withSeparator ? <TooltipSeparator /> : null}
      {mods.map((mod) => (
        <div className={className} key={mod.id}>
          {lc(renderPoeText(renderUniqueModText(mod, customValues)))}
        </div>
      ))}
    </>
  );
}

export function FlavourTextLines({ lines }: { lines: string[] }) {
  if (!lines.length) return null;
  return (
    <>
      <TooltipSeparator />
      {lines.map((line, index) => (
        <div className="poe2-flavourText" key={`${line}:${index}`}>
          {lc(line)}
        </div>
      ))}
    </>
  );
}

export function TooltipModLines({
  mods,
  customValues,
  className,
  withSeparator = true,
}: {
  mods: EditorModifier[];
  customValues: CustomValueState;
  className: string;
  withSeparator?: boolean;
}) {
  if (!mods.length) return null;
  return (
    <>
      {withSeparator ? <TooltipSeparator /> : null}
      {mods.map((mod) => (
        <div className={className} key={mod.id}>
          {lc(renderPoeText(renderModifierText(mod, customValues)))}
        </div>
      ))}
    </>
  );
}
