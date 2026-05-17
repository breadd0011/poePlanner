import type { ReactNode } from "react";
import type { Rarity } from "../../domain/equipment";
import { normalizeRangeDashes } from "../../domain/itemText";

export const SUBTYPE_LABELS: Record<string, string> = {
  str: "STR",
  dex: "DEX",
  int: "INT",
  str_dex: "STR/DEX",
  str_int: "STR/INT",
  dex_int: "DEX/INT",
};

export function rarityTextClass(rarity: Rarity): string {
  if (rarity === "Unique") return "rarity-unique";
  if (rarity === "Rare") return "rarity-rare";
  if (rarity === "Magic") return "rarity-magic";
  return "rarity-normal";
}

export function iconToWebPath(icon: string | null | undefined): string | null {
  if (!icon) return null;
  const normalizeLocalIconPath = (rawPath: string) => {
    const parts = rawPath.split("/").filter(Boolean);
    const uniqueIndex = parts.findIndex(
      (part) => part.toLowerCase() === "uniques",
    );
    if (uniqueIndex >= 0) {
      parts[uniqueIndex] = "uniques";
      if (parts[uniqueIndex + 1])
        parts[uniqueIndex + 1] = parts[uniqueIndex + 1].toLowerCase();
    }
    return parts.join("/");
  };
  if (icon.startsWith("Art/"))
    return `/image/${normalizeLocalIconPath(icon)}.webp`;
  if (icon.startsWith("/images/"))
    return icon.replace(/^\/images\//, "/image/");
  if (icon.startsWith("/image/")) return icon;
  return null;
}

export function TooltipSeparator() {
  return <div className="poe2-separator" />;
}

export function lc(content: ReactNode) {
  return <span className="poe2-lc">{content}</span>;
}

export function renderPoeText(text: string) {
  return normalizeRangeDashes(text);
}

export function rarityPopupClass(rarity: Rarity): string {
  if (rarity === "Unique") return "poe2-uniquePopup";
  if (rarity === "Rare") return "poe2-rarePopup";
  if (rarity === "Magic") return "poe2-magicPopup";
  return "poe2-normalPopup";
}

function formatRequirementNode(part: string) {
  const match = part.match(/^(Level|STR|DEX|INT)\s+(\d+)$/i);
  if (!match) return renderPoeText(part);
  const label = match[1].toUpperCase();
  if (label === "LEVEL") {
    return (
      <>
        Level <span className="poe2-colourDefault">{match[2]}</span>
      </>
    );
  }
  return (
    <>
      <span className="poe2-colourDefault">{match[2]}</span>{" "}
      {label === "STR" ? "Str" : label === "DEX" ? "Dex" : "Int"}
    </>
  );
}

export function JoinedRequirementLine({ parts }: { parts: string[] }) {
  return (
    <span>
      Requires{" "}
      {parts.map((part, index) => (
        <span key={`${part}:${index}`}>
          {index ? ", " : ""}
          {formatRequirementNode(part)}
        </span>
      ))}
    </span>
  );
}
