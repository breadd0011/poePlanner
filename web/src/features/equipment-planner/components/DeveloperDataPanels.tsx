import type { PlannerAugment, PlannerPocData } from "../../../types";
import { AppliedAugmentPreviewPanel } from "./debug-panels/AppliedAugmentPreviewPanel";
import { AugmentCoveragePanel } from "./debug-panels/AugmentCoveragePanel";
import { AugmentCataloguePanel } from "./debug-panels/AugmentCataloguePanel";
import { AugmentIndexAuditPanel } from "./debug-panels/AugmentIndexAuditPanel";
import { AugmentTooltip } from "./debug-panels/AugmentTooltip";
import { EditorModifierPools } from "./debug-panels/EditorModifierPools";
import { ItemTooltip } from "./debug-panels/ItemTooltip";
import { NormalExplicitPools } from "./debug-panels/NormalExplicitPools";
import { SubtypeSummary } from "./debug-panels/SubtypeSummary";

type Props = {
  data: PlannerPocData;
};

function augmentRegistry(data: PlannerPocData): PlannerAugment[] {
  return data.augments;
}

function hasAugmentWarnings(data: PlannerPocData): boolean {
  const coverageWarnings = data.parserSanity?.augmentCoverage?.validationWarnings ?? [];
  const catalogueWarnings = data.augmentCatalogue?.warnings ?? [];
  const socketWarnings = data.augmentCatalogue?.socketCandidateAudit?.validationWarnings ?? [];
  const indexWarnings = data.parserSanity?.augmentIndexAudit?.validationWarnings ?? [];
  return Boolean(coverageWarnings.length || catalogueWarnings.length || socketWarnings.length || indexWarnings.length);
}

export function DeveloperDataPanels({ data }: Props) {
  const augments = augmentRegistry(data);
  const openAugmentDiagnostics = hasAugmentWarnings(data);

  return (
    <details className="legacy-debug-panel">
      <summary>Developer data panels</summary>
      <details className="details-block" open={openAugmentDiagnostics}>
        <summary>Augment diagnostics</summary>
        <AugmentIndexAuditPanel audit={data.parserSanity?.augmentIndexAudit} />
        <AugmentCataloguePanel catalogue={data.augmentCatalogue} />
        <AugmentCoveragePanel augments={augments} coverage={data.parserSanity?.augmentCoverage} />
        <AppliedAugmentPreviewPanel augments={augments} />
      </details>

      <section className="grid">
        {data.items.map((item) => (
          <ItemTooltip item={item} key={item.id} />
        ))}
        {data.augment ? <AugmentTooltip augment={data.augment} /> : null}
      </section>

      <details className="details-block">
        <summary>All socket augment tooltip previews ({augments.length})</summary>
        <section className="grid">
          {augments.map((augment) => (
            <AugmentTooltip augment={augment} key={augment.id} />
          ))}
        </section>
      </details>

      <section className="subtype-grid">
        {data.itemSubtypes.map((subtype) => (
          <SubtypeSummary subtype={subtype} key={subtype.id} />
        ))}
      </section>

      <EditorModifierPools pools={data.editorModifierPools} sourceMechanics={data.modifierSourceMechanics} />
      <NormalExplicitPools pools={data.normalExplicitPools} />
    </details>
  );
}
