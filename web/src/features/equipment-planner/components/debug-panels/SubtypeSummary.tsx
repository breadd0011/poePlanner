import type { ItemSubtype } from "../../../../types";

function formatRequirements(requirements: Record<string, number | null>) {
  return Object.entries(requirements)
    .filter(([, value]) => value !== null)
    .map(([key, value]) => `${key.toUpperCase()}: ${value}`)
    .join(", ") || "—";
}

function formatDefences(defences: Record<string, number>) {
  return Object.entries(defences)
    .map(([key, value]) => `${key}: ${value}`)
    .join(", ");
}

export function SubtypeSummary({ subtype }: { subtype: ItemSubtype }) {
  const primaryPool = subtype.modGroups.find((group) => group.plannerPrimary);
  const comparison = subtype.modPoolComparisons[0];

  return (
    <article className="subtype-card">
      <header>
        <h2>{subtype.label}</h2>
        <p>
          {subtype.slug} · {subtype.attributeProfile.join("/")} · {subtype.defenceProfile.join("/")}
        </p>
      </header>

      <section>
        <h3>Base items ({subtype.baseItems.length})</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Defence</th>
              <th>Requirements</th>
            </tr>
          </thead>
          <tbody>
            {subtype.baseItems.slice(0, 8).map((item) => (
              <tr key={item.name}>
                <td>{item.name}</td>
                <td>{formatDefences(item.defences)}</td>
                <td>{formatRequirements(item.requirements)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {primaryPool ? (
        <section>
          <h3>Planner corrupted enchantments ({primaryPool.mods.length})</h3>
          <ul className="compact-list">
            {primaryPool.mods.map((mod) => (
              <li key={mod.id}>{mod.text}</li>
            ))}
          </ul>
          {comparison ? <p className="muted">Reference diff status: {comparison.status}</p> : null}
        </section>
      ) : null}

      {subtype.diagnostics.length > 0 ? (
        <section className="diagnostics">
          <h3>Diagnostics</h3>
          {subtype.diagnostics.map((diagnostic) => (
            <p key={diagnostic.code} className={`diagnostic diagnostic--${diagnostic.severity}`}>
              <strong>{diagnostic.severity.toUpperCase()}</strong> · {diagnostic.code}: {diagnostic.message}
            </p>
          ))}
        </section>
      ) : null}

      {subtype.warnings.length > 0 ? (
        <section className="warnings">
          <h3>Warnings</h3>
          {subtype.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </section>
      ) : null}
    </article>
  );
}
