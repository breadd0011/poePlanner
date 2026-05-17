import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { PayloadHealthUniqueClassReport, PlannerPocData } from "./types";
import { ItemEditor } from "./features/equipment-planner/components/ItemEditor";
import { createSlotCompatibilityMap } from "./features/equipment-planner/domain/equipment";
import { createSocketCapacityConfig } from "./features/equipment-planner/domain/itemSockets";
import { PayloadContractError, type PayloadContractIssue } from "./dataContract";
import { loadPlannerData, type LoadedPlannerData } from "./dataLoader";

const DATA_URL = "/data/poe2db_poc_ui.json";

const DeveloperDataPanels = lazy(() =>
  import("./features/equipment-planner/components/DeveloperDataPanels").then(
    (module) => ({ default: module.DeveloperDataPanels }),
  ),
);

function initialDeveloperPanelsVisible(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  return params.get("debugData") === "1" || window.location.hash === "#debug-data";
}

function ContractIssuesPanel({ issues }: { issues: PayloadContractIssue[] }) {
  if (!issues.length) return null;

  const errors = issues.filter((issue) => issue.severity === "error").length;
  const warnings = issues.length - errors;

  return (
    <section className="payload-contract-panel">
      <div className="payload-contract-panel__header">
        <strong>Payload contract</strong>
        <span>{errors} errors · {warnings} warnings</span>
      </div>
      <ul>
        {issues.map((issue) => (
          <li className={`payload-contract-panel__issue payload-contract-panel__issue--${issue.severity}`} key={issue.code}>
            <code>{issue.code}</code>
            {issue.message}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ErrorScreen({ message }: { message: string }) {
  return (
    <main className="app-shell">
      <header className="page-header">
        <h1>PoE2DB planner import POC</h1>
        <p className="error-text">{message}</p>
      </header>
    </main>
  );
}

export function App() {
  const [data, setData] = useState<PlannerPocData | null>(null);
  const [contractIssues, setContractIssues] = useState<PayloadContractIssue[]>([]);
  const [loadedDataInfo, setLoadedDataInfo] = useState<Pick<LoadedPlannerData, "source" | "loadedUrls"> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDeveloperData, setShowDeveloperData] = useState(initialDeveloperPanelsVisible);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const loaded = await loadPlannerData(DATA_URL);
        if (!cancelled) {
          setData(loaded.data);
          setContractIssues(loaded.issues);
          setLoadedDataInfo({ source: loaded.source, loadedUrls: loaded.loadedUrls });
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof PayloadContractError) {
          setContractIssues(err.issues);
        }
        setError(err instanceof Error ? err.message : String(err));
      }
    }

    void loadData();
    return () => {
      cancelled = true;
    };
  }, []);

  const slotCompatibility = useMemo(() => createSlotCompatibilityMap(data ?? undefined), [data]);
  const socketConfig = useMemo(() => createSocketCapacityConfig(data ?? undefined), [data]);

  if (error) return <ErrorScreen message={error} />;

  if (!data) {
    return (
      <main className="app-shell">
        <header className="page-header">
          <h1>PoE2DB planner import POC</h1>
          <p>Loading planner data from {DATA_URL}…</p>
        </header>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <h1>PoE2DB planner import POC</h1>
          <p>
            Schema: {data.schemaVersion} · Parser: {data.parserVersion} · Generated: {new Date(data.generatedAt).toLocaleString()}
          </p>
          <p>Data is loaded via fetch from <code>{DATA_URL}</code>, so the big JSON is no longer bundled into the app JS.</p>
          {loadedDataInfo ? (
            <p>Payload mode: {loadedDataInfo.source === "split_manifest" ? "split manifest" : "monolith"} · {loadedDataInfo.loadedUrls.length} fetched JSON file{loadedDataInfo.loadedUrls.length === 1 ? "" : "s"}</p>
          ) : null}
          {data.itemClasses.map((itemClass) => (
            <p key={itemClass.id}>
              {itemClass.itemClass}: {itemClass.summary.uniqueCount} uniques · {itemClass.summary.itemCount} item entries
            </p>
          ))}
          {Object.entries(data.uniqueItems.reduce<Record<string, number>>((counts, item) => {
            counts[item.itemClass] = (counts[item.itemClass] ?? 0) + 1;
            return counts;
          }, {})).map(([itemClass, count]) => (
            <p key={itemClass}>Imported unique {itemClass} display rows: {count}</p>
          ))}
          {data.parserSanity ? <p>Parser sanity: {data.parserSanity.importedUniqueItems ?? data.uniqueItems.length} uniques · {data.parserSanity.importedBaseItems ?? data.baseItems.length} base items · {data.parserSanity.loadedEditorModifierPools} editor pools loaded</p> : null}
          <ContractIssuesPanel issues={contractIssues} />
          {data.payloadHealth ? (
            <section className={`payload-health payload-health--${data.payloadHealth.status}`}>
              <div className="payload-health__header">
                <strong>Payload health: {data.payloadHealth.status.toUpperCase()}</strong>
                <span>{data.payloadHealth.warnings.length} warnings</span>
              </div>
              <div className="payload-health__grid">
                {Object.entries(data.payloadHealth.uniqueItems.byClass as Record<string, PayloadHealthUniqueClassReport>).map(([itemClass, report]) => (
                  <span key={itemClass}>
                    {itemClass}: {report.icon.withValue}/{report.total} icon · {report.flavourText.withValue}/{report.total} flavour · {report.explicitMods.withValue}/{report.total} mods
                  </span>
                ))}
              </div>
              {data.payloadHealth.modifierCoverage ? (
                <p>
                  Modifier coverage: {data.payloadHealth.modifierCoverage.summary.requiredClassesOk}/{data.payloadHealth.modifierCoverage.summary.requiredClasses} required classes OK · {data.payloadHealth.modifierCoverage.summary.experimentalClassesReady}/{data.payloadHealth.modifierCoverage.summary.experimentalClasses} experimental ready
                </p>
              ) : null}
              {data.payloadHealth.itemEditorBinding ? (
                <p>
                  Item editor binding: {data.payloadHealth.itemEditorBinding.summary.optionsWithEditorPools}/{data.payloadHealth.itemEditorBinding.summary.bindableItemOptions ?? data.payloadHealth.itemEditorBinding.summary.itemOptions} bindable editor-bound · {data.payloadHealth.itemEditorBinding.summary.optionsWithNormalExplicitPools}/{data.payloadHealth.itemEditorBinding.summary.bindableItemOptions ?? data.payloadHealth.itemEditorBinding.summary.itemOptions} bindable normal-bound · status {data.payloadHealth.itemEditorBinding.status}{data.payloadHealth.itemEditorBinding.summary.untypedSpecialItemOptions ? ` · ${data.payloadHealth.itemEditorBinding.summary.untypedSpecialItemOptions} untyped special` : ""}
                </p>
              ) : null}
              {data.payloadHealth.warnings.length ? <p>{data.payloadHealth.warnings[0].message}</p> : null}
            </section>
          ) : null}
        </div>
      </header>

      <ItemEditor
        subtypes={data.itemSubtypes}
        pools={data.editorModifierPools}
        baseItems={data.baseItems}
        uniqueItems={data.uniqueItems}
        sourceMechanics={data.modifierSourceMechanics}
        augments={data.augments}
        slotCompatibility={slotCompatibility}
        socketConfig={socketConfig}
        generatedItemOptions={data.ui?.itemEditor?.itemOptions ?? data.ui?.itemOptions ?? data.itemOptions}
      />

      <section className="developer-panel-toggle">
        <button type="button" onClick={() => setShowDeveloperData((current) => !current)}>
          {showDeveloperData ? "Hide" : "Show"} developer data panels
        </button>
        <span>Debug panels are lazy-mounted so they stay out of the normal planner render path.</span>
      </section>

      {showDeveloperData ? (
        <Suspense fallback={<p>Loading developer data panels…</p>}>
          <DeveloperDataPanels data={data} />
        </Suspense>
      ) : null}
    </main>
  );
}
