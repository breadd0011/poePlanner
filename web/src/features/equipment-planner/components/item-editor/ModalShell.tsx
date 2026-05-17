import { useId, useRef, type ReactNode } from "react";
import { useModalFocusTrap } from "../../hooks/useModalFocusTrap";

export function ModalShell({
  title,
  subtitle,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const subtitleId = useId();
  const dialogRef = useRef<HTMLElement>(null);

  useModalFocusTrap({ ref: dialogRef, onClose });

  return (
    <div
      className="planner-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        aria-describedby={subtitle ? subtitleId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={`planner-modal-shell ${wide ? "planner-modal-shell--wide" : ""}`}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="planner-modal-header">
          <div>
            <strong id={titleId}>{title}</strong>
            {subtitle ? <p id={subtitleId}>{subtitle}</p> : null}
          </div>
          <button type="button" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
