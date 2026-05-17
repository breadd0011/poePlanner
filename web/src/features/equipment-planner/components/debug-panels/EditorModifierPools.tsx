import { useMemo } from "react";
import type { EditorModifierPool, ModifierSourceMechanic } from "../../../../types";

function displayKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(/[_\s]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function EditorModifierPools({
  pools,
  sourceMechanics = [],
}: {
  pools: EditorModifierPool[];
  sourceMechanics?: ModifierSourceMechanic[];
}) {
  const sourceLabels = useMemo(() => {
    const labels: Record<string, string> = {};
    for (const source of sourceMechanics) labels[source.id] = source.label;
    for (const pool of pools) {
      if (!labels[pool.sourceMechanic]) labels[pool.sourceMechanic] = displayKey(pool.sourceMechanic);
    }
    return labels;
  }, [pools, sourceMechanics]);

  if (!pools.length) return null;
  const groups = [...new Set(pools.map((pool) => `${pool.itemClass}:${pool.subtype}`))];
  return (
    <section className="normal-pools">
      <header>
        <h2>Editor modifier pools</h2>
        <p>All parsed ModifiersCalc groups for the supported item classes. Augment and Bonded here mean compatible item-editor options from these pages, not the full standalone augment item scraper.</p>
      </header>
      {groups.map((group) => {
        const [itemClass, subtype] = group.split(":");
        const subtypePools = pools.filter((pool) => pool.itemClass === itemClass && pool.subtype === subtype);
        return (
          <article className="subtype-card" key={group}>
            <header>
              <h3>{itemClass} / {subtype}</h3>
              <p>{subtypePools.length} source groups</p>
            </header>
            <div className="pool-summary-grid">
              {subtypePools.map((pool) => (
                <div className="pool-summary-card" key={pool.id}>
                  <strong>{pool.sourceGroup}</strong>
                  <span>{sourceLabels[pool.sourceMechanic] ?? displayKey(pool.sourceMechanic)}</span>
                  <small>{pool.mods.length} mods</small>
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </section>
  );
}
