import type { NormalExplicitPool } from "../../../../types";

function AffixList({ title, mods }: { title: string; mods: NormalExplicitPool["prefixes"] }) {
  return (
    <section>
      <h3>{title} ({mods.length})</h3>
      <ul className="compact-list affix-list">
        {mods.map((mod) => (
          <li key={mod.id}>
            <div className="affix-row-main">
              <span>{mod.text}</span>
              {mod.detailStatus === "available" ? <em>details available</em> : null}
            </div>
            {mod.tags.length ? <small>{mod.tags.join(" · ")}</small> : null}
            <small className="affix-meta">
              {mod.family ? <>family: {mod.family}</> : <>family: —</>}
              {mod.level !== null ? <> · level: {mod.level}</> : null}
              {mod.tierCount !== null ? <> · tiers: {mod.tierCount}</> : null}
              {mod.weightRaw ? <> · weight: {mod.weightRaw}</> : null}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function NormalExplicitPools({ pools }: { pools: NormalExplicitPool[] }) {
  if (pools.length === 0) return null;

  return (
    <section className="normal-pools">
      <header>
        <h2>Simple editor affix pools</h2>
        <p>Planner-facing Base Prefix/Base Suffix lists. This is family-level editor data, not crafting/tier simulation.</p>
      </header>
      {pools.map((pool) => (
        <article className="subtype-card" key={pool.id}>
          <header>
            <h3>{pool.itemClass} / {pool.subtype}</h3>
            <p>{pool.sourceSection} · confidence: {pool.confidence} · sources: {pool.rawSources.join(", ")}</p>
          </header>
          <div className="affix-grid">
            <AffixList title="Base Prefix" mods={pool.prefixes} />
            <AffixList title="Base Suffix" mods={pool.suffixes} />
          </div>
        </article>
      ))}
    </section>
  );
}
