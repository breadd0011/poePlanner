import {
  RARITIES,
  type ItemOption,
  type Rarity,
} from "../../domain/equipment";

function ItemSelect({
  options,
  selectedItemId,
  onSelect,
}: {
  options: ItemOption[];
  selectedItemId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <label className="editor-field">
      <span>Item</span>
      <select
        value={selectedItemId}
        onChange={(event) => onSelect(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ItemEditorHeaderForm({
  customName,
  isCorrupted,
  isSanctified,
  itemLevel,
  itemOptions,
  rarity,
  safeQuality,
  selectedItemId,
  selectedSocketCount,
  maxSocketCount,
  onCorruptedChange,
  onCustomNameChange,
  onItemLevelChange,
  onItemSelect,
  onQualityChange,
  onRarityChange,
  onSanctifiedChange,
  onSocketCountChange,
}: {
  customName: string;
  isCorrupted: boolean;
  isSanctified: boolean;
  itemLevel: number;
  itemOptions: ItemOption[];
  rarity: Rarity;
  safeQuality: number;
  selectedItemId: string;
  selectedSocketCount: number;
  maxSocketCount: number;
  onCorruptedChange: (checked: boolean) => void;
  onCustomNameChange: (value: string) => void;
  onItemLevelChange: (value: number) => void;
  onItemSelect: (id: string) => void;
  onQualityChange: (value: number) => void;
  onRarityChange: (value: Rarity) => void;
  onSanctifiedChange: (checked: boolean) => void;
  onSocketCountChange: (value: number) => void;
}) {
  const selectedOption = itemOptions.find((option) => option.id === selectedItemId);
  const originalItemName = selectedOption?.name || selectedOption?.baseName || "Item name";
  const highestSocketOption = Math.max(0, maxSocketCount, selectedSocketCount);
  const socketCountOptions = Array.from(
    { length: highestSocketOption + 1 },
    (_, value) => value,
  );

  return (
    <div className="item-header-panel item-editor-header-panel item-header-panel--compact">
      <div className="item-option-stack">
        <div className="item-editor-options">
          <label className="editor-field">
            <span>Name</span>
            <input
              value={customName}
              placeholder={originalItemName}
              onChange={(event) => onCustomNameChange(event.target.value)}
            />
          </label>
          <ItemSelect
            options={itemOptions}
            selectedItemId={selectedItemId}
            onSelect={onItemSelect}
          />
          <label className="editor-field">
            <span>Rarity</span>
            <select
              value={rarity}
              onChange={(event) => onRarityChange(event.target.value as Rarity)}
            >
              {RARITIES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="editor-field">
            <span>Item Level</span>
            <input
              type="number"
              min={1}
              max={100}
              value={itemLevel}
              onChange={(event) =>
                onItemLevelChange(Number(event.target.value) || 1)
              }
            />
          </label>
          <label className="editor-field">
            <span>Quality</span>
            <input
              type="number"
              min={0}
              max={30}
              value={safeQuality}
              onChange={(event) =>
                onQualityChange(
                  Math.max(0, Math.min(30, Number(event.target.value) || 0)),
                )
              }
            />
          </label>
          <label className="editor-field editor-field--socket-count">
            <span>Augment Sockets</span>
            <select
              value={selectedSocketCount}
              onChange={(event) =>
                onSocketCountChange(Number(event.target.value))
              }
            >
              {socketCountOptions.map((value) => (
                <option key={value} value={value}>
                  {value} {value === 1 ? "socket" : "sockets"}{value >= 3 ? " (corrupted)" : ""}
                </option>
              ))}
            </select>
          </label>
          <div className="editor-checkbox-stack">
            <label className="editor-checkbox">
              <span>Corrupted</span>
              <input
                type="checkbox"
                checked={isCorrupted}
                onChange={(event) => onCorruptedChange(event.target.checked)}
              />
            </label>
            <label className="editor-checkbox">
              <span>Sanctified</span>
              <input
                type="checkbox"
                checked={isSanctified}
                onChange={(event) => onSanctifiedChange(event.target.checked)}
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
