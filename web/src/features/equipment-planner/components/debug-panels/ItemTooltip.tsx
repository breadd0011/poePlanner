import type { PlannerItem } from "../../../../types";
import { TooltipSection } from "./TooltipSection";

type Props = {
  item: PlannerItem;
};

export function ItemTooltip({ item }: Props) {
  return (
    <article className={`tooltip-card tooltip-card--${item.rarity?.toLowerCase() ?? "normal"}`}>
      <header className="card-meta">
        <span>{item.kind}</span>
        <span>{item.id}</span>
        {item.rarity ? <span>{item.rarity}</span> : null}
        {item.itemClass ? <span>{item.itemClass}</span> : null}
      </header>

      <div className="tooltip-box">
        {item.tooltipSections.map((section, index) => (
          <TooltipSection section={section} key={`${item.name}-${section.kind}-${index}`} />
        ))}
      </div>

      <details className="details-block">
        <summary>Parsed mods ({item.mods.length})</summary>
        {item.mods.length === 0 ? (
          <p>No parsed mod blocks.</p>
        ) : (
          item.mods.map((mod) => (
            <div className="mod-block" key={`${item.name}-${mod.text}-${mod.family ?? "none"}`}>
              <strong>{mod.text}</strong>
              <div className="mod-meta">
                {mod.family ? <span>Family: {mod.family}</span> : null}
                {mod.generationType ? <span>Generation: {mod.generationType}</span> : null}
                {mod.requiredLevel != null ? <span>Req. level: {mod.requiredLevel}</span> : null}
              </div>
              {mod.stats.map((stat) => (
                <code className="stat-line" key={stat.raw}>
                  {stat.raw}
                </code>
              ))}
            </div>
          ))
        )}
      </details>

      <details className="details-block">
        <summary>Normalized planner data</summary>
        <pre>{JSON.stringify(item.normalized ?? {}, null, 2)}</pre>
      </details>

      <details className="details-block">
        <summary>Object data</summary>
        <pre>{JSON.stringify(item.objectData ?? {}, null, 2)}</pre>
      </details>
    </article>
  );
}
