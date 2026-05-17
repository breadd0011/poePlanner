export function ItemEditorActions({
  onBackToBrowser,
  onEquip,
}: {
  onBackToBrowser: () => void;
  onEquip: () => void;
}) {
  return (
    <div className="planner-modal-actions planner-modal-actions--simple">
      <button
        type="button"
        className="planner-back-button"
        onClick={onBackToBrowser}
        aria-label="Back to browser"
        title="Back to browser"
      >
        ←
      </button>
      <button type="button" className="planner-equip-button" onClick={onEquip}>
        Equip
      </button>
    </div>
  );
}
