import type { AugmentCatalogue, AugmentCatalogueEntry } from "../../../../types";

function formatRecord(record?: Record<string, number>): string {
  if (!record || !Object.keys(record).length) return "—";
  return Object.entries(record)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
}

function sectionRows(entries: AugmentCatalogueEntry[]) {
  const bySection = new Map<string, AugmentCatalogueEntry[]>();
  for (const entry of entries) {
    const section = entry.section || "Unknown";
    bySection.set(section, [...(bySection.get(section) ?? []), entry]);
  }
  return Array.from(bySection.entries()).sort(([a], [b]) => a.localeCompare(b));
}

function sampleNames(entries: AugmentCatalogueEntry[]): string {
  const names = entries.map((entry) => entry.name).filter(Boolean).slice(0, 10);
  if (!names.length) return "—";
  return entries.length > names.length ? `${names.join(", ")}, +${entries.length - names.length} more` : names.join(", ");
}

function categoryCounts(entries: AugmentCatalogueEntry[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const entry of entries) {
    const category = entry.category || "unknown";
    counts[category] = (counts[category] ?? 0) + 1;
  }
  return counts;
}

function countDetails(entries: AugmentCatalogueEntry[], status: string): number {
  return entries.filter((entry) => (entry.detailStatus || "index_only") === status).length;
}

function countWithEffects(entries: AugmentCatalogueEntry[]): number {
  return entries.filter((entry) => (entry.normalEffectCount ?? 0) + (entry.bondedEffectCount ?? 0) > 0).length;
}

function warningClass(severity: string): string {
  return `augment-warning augment-warning--${severity || "warning"}`;
}

export function AugmentCataloguePanel({ catalogue }: { catalogue?: AugmentCatalogue | null }) {
  if (!catalogue?.entries.length) return null;

  const socketCandidates = catalogue.entries.filter((entry) => entry.socketCandidate);
  const catalogueOnly = catalogue.entries.filter((entry) => !entry.socketCandidate);
  const socketAudit = catalogue.socketCandidateAudit;
  const socketWarnings = socketAudit?.validationWarnings ?? [];

  return (
    <section className="augment-catalogue-panel">
      <header>
        <h2>Augment catalogue registry</h2>
        <p>
          Registry generated from the full Augment index. Socket candidates are derived from game data: Rune Item entries plus detail pages that expose Augment Socket usage or equipment-targeted augment effects.
        </p>
      </header>

      <div className="augment-coverage-grid">
        <span>
          <strong>{catalogue.total}</strong>
          <small>catalogue entries</small>
        </span>
        <span>
          <strong>{catalogue.socketCandidateCount}</strong>
          <small>socket picker candidates</small>
        </span>
        {socketAudit && (
          <>
            <span>
              <strong>{socketAudit.runeItemCandidates}</strong>
              <small>Rune Item candidates</small>
            </span>
            <span>
              <strong>{socketAudit.soulCoreCandidates}</strong>
              <small>Soul Core candidates</small>
            </span>
            <span>
              <strong>{socketAudit.otherSocketableAugments}</strong>
              <small>other socket augments</small>
            </span>
            <span>
              <strong>{socketAudit.excludedReferenceEntries}</strong>
              <small>excluded ref entries</small>
            </span>
          </>
        )}
        <span>
          <strong>{catalogueOnly.length}</strong>
          <small>catalogue-only entries</small>
        </span>
        <span>
          <strong>{catalogue.detailLoadedCount ?? countDetails(catalogue.entries, "detail_loaded")}</strong>
          <small>details loaded</small>
        </span>
        <span>
          <strong>{catalogue.indexOnlyCount ?? countDetails(catalogue.entries, "index_only")}</strong>
          <small>index-only entries</small>
        </span>
        <span>
          <strong>{catalogue.entriesWithEffects ?? countWithEffects(catalogue.entries)}</strong>
          <small>entries with effects</small>
        </span>
        <span>
          <strong>{formatRecord(catalogue.categoryCounts)}</strong>
          <small>category buckets</small>
        </span>
      </div>

      <div className="augment-catalogue-details">
        <p><strong>Sections:</strong> {formatRecord(catalogue.sectionCounts)}</p>
        <p><strong>Detail statuses:</strong> {formatRecord(catalogue.detailStatusCounts)}</p>
        <p><strong>Detail sources:</strong> {formatRecord(catalogue.detailSourceCounts)}</p>
        <p><strong>Socket picker source:</strong> {socketCandidates.length ? "Game-compatible socket augment entries" : "No socket candidates parsed"}</p>
        {socketAudit && (
          <>
            <p><strong>Socket candidates by category:</strong> {formatRecord(socketAudit.socketCandidatesByCategory)}</p>
            <p><strong>Socket candidates by reason:</strong> {formatRecord(socketAudit.socketCandidatesByReason)}</p>
          </>
        )}
      </div>

      {socketAudit && (
        <details className="augment-validation-details" open={socketWarnings.length > 0}>
          <summary>Socket-compatible guardrails ({socketWarnings.length} warning/error{socketWarnings.length === 1 ? "" : "s"})</summary>
          <p>These checks keep the picker limited to game-supported Augment Socket items. They do not imply full-character DPS calculation; they only validate item-level weapon/armour stat augment entries.</p>
          {socketWarnings.length ? (
            <ul>
              {socketWarnings.slice(0, 24).map((warning, index) => (
                <li className={warningClass(warning.severity)} key={`${warning.code}-${warning.augmentName ?? index}`}>
                  <span>{warning.severity}</span>
                  <code>{warning.code}</code>
                  {warning.augmentName && <strong>{warning.augmentName}</strong>}
                  {warning.message}
                </li>
              ))}
            </ul>
          ) : (
            <p>No socket-compatible guardrail warnings.</p>
          )}
        </details>
      )}

      <div className="augment-index-section-table-wrap">
        <table className="augment-index-section-table">
          <thead>
            <tr>
              <th>Section</th>
              <th>Entries</th>
              <th>Socket candidates</th>
              <th>Categories</th>
              <th>Detail status</th>
              <th>Effects</th>
              <th>Sample entries</th>
            </tr>
          </thead>
          <tbody>
            {sectionRows(catalogue.entries).map(([section, entries]) => (
              <tr key={section}>
                <td>{section}</td>
                <td>{entries.length}</td>
                <td>{entries.filter((entry) => entry.socketCandidate).length}</td>
                <td>{formatRecord(categoryCounts(entries))}</td>
                <td>{formatRecord(entries.reduce<Record<string, number>>((counts, entry) => {
                  const status = entry.detailStatus || "index_only";
                  counts[status] = (counts[status] ?? 0) + 1;
                  return counts;
                }, {}))}</td>
                <td>{countWithEffects(entries)} / {entries.length}</td>
                <td>{sampleNames(entries)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {catalogue.warnings.length > 0 && (
        <details className="augment-validation-details">
          <summary>Catalogue warnings ({catalogue.warnings.length})</summary>
          <ul>
            {catalogue.warnings.slice(0, 20).map((warning, index) => (
              <li className="augment-warning augment-warning--warning" key={`${warning}-${index}`}>
                <span>warning</span>
                <code>augment_catalogue</code>
                {warning}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
