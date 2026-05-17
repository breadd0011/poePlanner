import type { TooltipSection as TooltipSectionType } from "../../../../types";

type Props = {
  section: TooltipSectionType;
};

const conditionLabels: Record<string, string> = {
  martial_weapon: "Martial Weapon",
  wand_or_staff: "Wand or Staff",
  armour: "Armour",
  all_equipment: "All Equipment",
};

function titleForSection(section: TooltipSectionType): string | null {
  switch (section.kind) {
    case "requirement":
      return "Requires";
    case "explicit":
      return "Explicit";
    case "implicit":
      return "Implicit";
    case "description":
      return "Description";
    case "augment_effect":
      return `${section.bonded ? "Bonded · " : ""}${conditionLabels[section.condition] ?? section.condition}`;
    default:
      return null;
  }
}

export function TooltipSection({ section }: Props) {
  const title = titleForSection(section);

  return (
    <section className={`tooltip-section tooltip-section--${section.kind}`}>
      {title ? <div className="section-label">{title}</div> : null}
      {section.lines.map((line, index) => (
        <div className="tooltip-line" key={`${section.kind}-${index}-${line}`}>
          {line}
        </div>
      ))}
    </section>
  );
}
