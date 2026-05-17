import type { PlannerAugment, ParserSanityReport } from "../../../../types";

type AugmentCoverage = NonNullable<ParserSanityReport["augmentCoverage"]>;

function shortList(names: string[]): string {
  if (!names.length) return "—";
  const visible = names.slice(0, 8).join(", ");
  return names.length > 8 ? `${visible}, +${names.length - 8} more` : visible;
}

function formatRecord(record?: Record<string, string | string[] | number>): string {
  if (!record || !Object.keys(record).length) return "—";
  return Object.entries(record)
    .slice(0, 8)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join("; ") : value}`)
    .join(" · ");
}

function warningLabel(coverage?: AugmentCoverage): string {
  const counts = coverage?.warningCounts ?? {};
  const errors = counts.error ?? 0;
  const warnings = counts.warning ?? 0;
  const infos = counts.info ?? 0;
  if (!errors && !warnings && !infos) return "no warnings";
  return `${errors} error · ${warnings} warning · ${infos} info`;
}

function warningClass(severity: string): string {
  if (severity === "error") return "augment-warning augment-warning--error";
  if (severity === "info") return "augment-warning augment-warning--info";
  return "augment-warning augment-warning--warning";
}

export function AugmentCoveragePanel({
  augments,
  coverage,
}: {
  augments: PlannerAugment[];
  coverage?: AugmentCoverage;
}) {
  if (!augments.length && !coverage) return null;

  if (!coverage) {
    return (
      <section className="augment-coverage-panel augment-coverage-panel--partial">
        <header>
          <h2>Rune augment coverage</h2>
          <p>Coverage data is missing from the scraper payload, so the UI is not synthesizing a fallback report.</p>
        </header>
        <div className="augment-coverage-grid">
          <span>
            <strong>{augments.length}</strong>
            <small>runtime augments loaded</small>
          </span>
        </div>
      </section>
    );
  }

  const report = coverage;
  const status = report.complete ? "ok" : "partial";
  const validationWarnings = report.validationWarnings ?? [];
  const blockingWarnings = validationWarnings.filter((warning) => warning.severity === "error" || warning.severity === "warning");

  return (
    <section className={`augment-coverage-panel augment-coverage-panel--${status}`}>
      <header>
        <h2>Rune augment coverage</h2>
        <p>
          Full Rune Item coverage target: {report.expected}. This validates the Rune Item subset; additional game-compatible socket augments, such as Soul Cores, can also exist in the planner-facing augment registry.
        </p>
      </header>
      <div className="augment-coverage-grid">
        <span>
          <strong>{report.loaded}</strong>
          <small>loaded / {report.expected}</small>
        </span>
        <span>
          <strong>{report.discovered}</strong>
          <small>discovered in index</small>
        </span>
        <span>
          <strong>{report.withNormalEffects}</strong>
          <small>with normal effects</small>
        </span>
        <span>
          <strong>{report.withCompleteNormalConditionSets ?? "—"}</strong>
          <small>complete normal condition sets</small>
        </span>
        <span>
          <strong>{report.withBondedEffects}</strong>
          <small>with bonded effects</small>
        </span>
        <span>
          <strong>{report.withIcons}</strong>
          <small>with icons</small>
        </span>
        <span>
          <strong>{report.withRequirements}</strong>
          <small>with requirements</small>
        </span>
        <span>
          <strong>{warningLabel(report)}</strong>
          <small>validation result</small>
        </span>
        <span>
          <strong>{report.conditions.length}</strong>
          <small>{report.conditions.join(" · ") || "no conditions"}</small>
        </span>
      </div>
      <div className="augment-coverage-details">
        <p><strong>Data sources:</strong> {formatRecord(report.dataSourceCounts)}</p>
        <p><strong>Missing normal effects:</strong> {shortList(report.missingNormalEffects)}</p>
        <p><strong>Missing normal condition sets:</strong> {formatRecord(report.missingNormalConditions)}</p>
        <p><strong>Suspicious effect text:</strong> {formatRecord(report.suspiciousEffectTexts)}</p>
        <p><strong>Empty Stack Size rows:</strong> {shortList(report.emptyStackSizeProperties ?? [])}</p>
        <p><strong>Duplicate property rows:</strong> {formatRecord(report.duplicatePropertyLines)}</p>
        <p><strong>Missing bonded effects:</strong> {shortList(report.missingBondedEffects)}</p>
        <p><strong>Missing icons:</strong> {shortList(report.missingIcons)}</p>
        <p><strong>No level requirement row:</strong> {shortList(report.missingRequirements)}</p>
      </div>

      {validationWarnings.length > 0 && (
        <details className="augment-validation-details" open={blockingWarnings.length > 0}>
          <summary>Validation warnings ({validationWarnings.length})</summary>
          <ul>
            {validationWarnings.slice(0, 40).map((warning, index) => (
              <li className={warningClass(warning.severity)} key={`${warning.code}-${warning.augmentName ?? "global"}-${index}`}>
                <span>{warning.severity}</span>
                <code>{warning.code}</code>
                {warning.message}
              </li>
            ))}
          </ul>
          {validationWarnings.length > 40 && (
            <p>Showing first 40 warnings, +{validationWarnings.length - 40} more in the generated JSON.</p>
          )}
        </details>
      )}
    </section>
  );
}
