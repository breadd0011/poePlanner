import type { ItemOption } from "../../domain/equipment";
import { displayKey } from "../../domain/itemText";
import type { BrowserKindFilter } from "./editorTypes";
import { ItemIcon } from "./ItemIcon";
import { iconToWebPath } from "./itemPresentation";

function ItemBrowserRow({
  option,
  onSelect,
}: {
  option: ItemOption;
  onSelect: (option: ItemOption) => void;
}) {
  return (
    <button
      type="button"
      className="item-browser-row"
      onClick={() => onSelect(option)}
    >
      <ItemIcon
        label={
          option.kind === "unique"
            ? "U"
            : option.itemClass.slice(0, 2).toUpperCase()
        }
        iconPath={iconToWebPath(option.icon)}
      />
      <span className="item-browser-row__main">
        <strong
          className={
            option.kind === "unique" ? "rarity-unique" : "rarity-normal"
          }
        >
          {option.name}
        </strong>
        <small>
          {option.baseName} · {option.itemClass} ·{" "}
          {option.kind === "unique" ? "Unique" : displayKey(option.subtype)}
        </small>
      </span>
    </button>
  );
}

export function ItemBrowser({
  activeSlotLabel,
  query,
  kind,
  visibleOptions,
  compatibleClassCount,
  onQueryChange,
  onKindChange,
  onSelect,
}: {
  activeSlotLabel: string;
  query: string;
  kind: BrowserKindFilter;
  visibleOptions: ItemOption[];
  compatibleClassCount: number;
  onQueryChange: (value: string) => void;
  onKindChange: (value: BrowserKindFilter) => void;
  onSelect: (option: ItemOption) => void;
}) {
  return (
    <>
      <div className="item-browser-controls">
        <label className="editor-field">
          <span>Search</span>
          <input
            autoFocus
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={`Search ${activeSlotLabel} items`}
          />
        </label>
        <label className="editor-field">
          <span>Kind</span>
          <select
            value={kind}
            onChange={(event) =>
              onKindChange(event.target.value as BrowserKindFilter)
            }
          >
            <option value="all">Base + Unique</option>
            <option value="base">Base only</option>
            <option value="unique">Unique only</option>
          </select>
        </label>
      </div>
      <div className="item-browser-summary">
        {visibleOptions.length} matching items · {compatibleClassCount} compatible
        classes
      </div>
      <div className="item-browser-list">
        {visibleOptions.length ? (
          visibleOptions.map((option) => (
            <ItemBrowserRow
              key={option.id}
              option={option}
              onSelect={onSelect}
            />
          ))
        ) : (
          <p className="item-browser-empty">
            No valid items found for this slot/filter.
          </p>
        )}
      </div>
    </>
  );
}
