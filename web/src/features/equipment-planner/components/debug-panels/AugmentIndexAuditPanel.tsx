import type { AugmentIndexAudit } from "../../../../types";

function formatRecord(record?: Record<string, number>): string {
  if (!record || !Object.keys(record).length) return "—";
  return Object.entries(record)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
}

function sectionStatus(section: AugmentIndexAudit["sections"][number]): string {
  if (section.expected == null) return `${section.discovered}`;
  return `${section.discovered} / ${section.expected}`;
}

function firstEntries(section: AugmentIndexAudit["sections"][number]): string {
  const names = section.entries.map((entry) => entry.name).filter(Boolean).slice(0, 8);
  if (!names.length) return "—";
  return section.entries.length > names.length ? `${names.join(", ")}, +${section.entries.length - names.length} more` : names.join(", ");
}

function warningClass(severity: string): string {
  if (severity === "error") return "augment-warning augment-warning--error";
  if (severity === "info") return "augment-warning augment-warning--info";
  return "augment-warning augment-warning--warning";
}

export function AugmentIndexAuditPanel({ audit }: { audit?: AugmentIndexAudit }) {
  if (!audit) return null;

  const warnings = audit.validationWarnings ?? [];
  const augmentItem = audit.sections.find((section) => section.section === "Augment Item");
  const runeItem = audit.sections.find((section) => section.section === "Rune Item");

  return (
    <section className={`augment-index-audit-panel augment-index-audit-panel--${audit.complete ? "ok" : "partial"}`}>
      <header>
        <h2>Augment index classification audit</h2>
        <p>
          Read-only audit for the full PoE2DB Augment catalogue. This does not add the full 123 entries to the picker yet; Rune Item remains the only socket picker source.
        </p>
      </header>

      <div className="augment-coverage-grid">
        <span>
          <strong>{augmentItem ? sectionStatus(augmentItem) : "—"}</strong>
          <small>Augment Item section</small>
        </span>
        <span>
          <strong>{runeItem ? sectionStatus(runeItem) : "—"}</strong>
          <small>Rune Item section</small>
        </span>
        <span>
          <strong>{audit.discoveredTotal}</strong>
          <small>catalogue links discovered</small>
        </span>
        <span>
          <strong>{formatRecord(audit.categoryCounts)}</strong>
          <small>classification buckets</small>
        </span>
      </div>

      <div className="augment-index-section-table-wrap">
        <table className="augment-index-section-table">
          <thead>
            <tr>
              <th>Section</th>
              <th>Discovered</th>
              <th>Socket candidates</th>
              <th>Categories</th>
              <th>Sample entries</th>
            </tr>
          </thead>
          <tbody>
            {audit.sections.map((section) => (
              <tr key={section.section}>
                <td>{section.section}</td>
                <td>{sectionStatus(section)}</td>
                <td>{section.socketCandidateCount}</td>
                <td>{formatRecord(section.categoryCounts)}</td>
                <td>{firstEntries(section)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {warnings.length > 0 && (
        <details className="augment-validation-details" open>
          <summary>Classification warnings ({warnings.length})</summary>
          <ul>
            {warnings.slice(0, 20).map((warning, index) => (
              <li className={warningClass(warning.severity)} key={`${warning.code}-${warning.section ?? "global"}-${index}`}>
                <span>{warning.severity}</span>
                <code>{warning.section ? `${warning.section}:${warning.code}` : warning.code}</code>
                {warning.message}
              </li>
            ))}
          </ul>
          {warnings.length > 20 && <p>Showing first 20 warnings, +{warnings.length - 20} more in generated JSON.</p>}
        </details>
      )}
    </section>
  );
}
