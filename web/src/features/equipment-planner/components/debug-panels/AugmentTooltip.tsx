import type { PlannerAugment } from "../../../../types";
import { AugmentTooltipPreview } from "../item-editor/AugmentTooltipPreview";
import { TooltipSection } from "./TooltipSection";

type Props = {
  augment: PlannerAugment;
};

export function AugmentTooltip({ augment }: Props) {
  return (
    <article className="tooltip-card tooltip-card--augment">
      <header className="card-meta">
        <span>{augment.kind}</span>
        <span>{augment.id}</span>
        {augment.itemClass ? <span>{augment.itemClass}</span> : null}
      </header>

      <div className="tooltip-box tooltip-box--poe-preview">
        <AugmentTooltipPreview augment={augment} />
      </div>

      <details className="details-block">
        <summary>Raw tooltip sections</summary>
        <div className="tooltip-box tooltip-box--raw-sections">
          {augment.tooltipSections.map((section, index) => (
            <TooltipSection section={section} key={`${augment.name}-${section.kind}-${index}`} />
          ))}
        </div>
      </details>

      <details className="details-block">
        <summary>Normalized augment effects</summary>
        <pre>{JSON.stringify(augment.augmentEffects ?? [], null, 2)}</pre>
      </details>

      <details className="details-block">
        <summary>Object data</summary>
        <pre>{JSON.stringify(augment.objectData ?? {}, null, 2)}</pre>
      </details>
    </article>
  );
}
