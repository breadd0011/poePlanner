import {
  equipmentSlots,
  getSlotLabel,
  type EquippedPreview,
  type EquipmentSlotDef,
  type SlotKey,
} from "../../domain/equipment";
import { rarityTextClass } from "./itemPresentation";
import { SocketedItemArtwork } from "./SocketedItemPreview";

function EquipmentSlotBox({
  slot,
  item,
  onClick,
}: {
  slot: EquipmentSlotDef;
  item?: EquippedPreview;
  onClick: (slot: SlotKey) => void;
}) {
  const isWeapon = slot.id === "weapon1" || slot.id === "weapon2";
  return (
    <button
      type="button"
      onClick={() => onClick(slot.id)}
      aria-label={slot.label || getSlotLabel(slot.id)}
      className={`equipment-slot-box equipment-slot-box--${slot.id} equipment-slot-box--${slot.tone ?? "default"} ${isWeapon ? "equipment-slot-box--weapon" : ""}`}
      style={{
        "--equipment-slot-left": slot.left,
        "--equipment-slot-top": slot.top,
        "--equipment-slot-width": slot.width,
        "--equipment-slot-height": slot.height,
      } as React.CSSProperties}
    >
      <div className="equipment-slot-inner">
        {item ? (
          <div className="equipped-preview">
            <SocketedItemArtwork
              className="socketed-item-artwork--equipped"
              iconPath={item.icon ?? null}
              label={item.name}
              socketCapacity={item.socketCapacity ?? 0}
              socketFilledCount={item.socketFilledCount ?? 0}
              socketAugments={item.socketAugments ?? []}
            />
            <strong className={rarityTextClass(item.rarity)}>
              {item.name}
            </strong>
            <span>{item.baseName}</span>
          </div>
        ) : null}
      </div>
      {slot.hasTabs ? (
        <span className="weapon-set-tabs" aria-hidden="true">
          <i>I</i>
          <i>II</i>
        </span>
      ) : null}
    </button>
  );
}

export function EquipmentBoard({
  equipped,
  openSlot,
}: {
  equipped: Partial<Record<SlotKey, EquippedPreview>>;
  openSlot: (slot: SlotKey) => void;
}) {
  return (
    <section className="equipment-board-shell" aria-label="Equipment slots">
      <div className="equipment-board">
        <div
          className="equipment-board-art equipment-board-art--charms"
          aria-hidden="true"
        />
        <div
          className="equipment-board-art equipment-board-art--life-left"
          aria-hidden="true"
        />
        <div
          className="equipment-board-art equipment-board-art--mana-right"
          aria-hidden="true"
        />
        <div
          className="equipment-board-ghost equipment-board-ghost--left"
          aria-hidden="true"
        />
        <div
          className="equipment-board-ghost equipment-board-ghost--right"
          aria-hidden="true"
        />
        {equipmentSlots.map((slot) => (
          <EquipmentSlotBox
            key={slot.id}
            slot={slot}
            item={equipped[slot.id]}
            onClick={openSlot}
          />
        ))}
      </div>
    </section>
  );
}
