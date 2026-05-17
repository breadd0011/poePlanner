import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function isFocusable(element: HTMLElement): boolean {
  if (element.hasAttribute("disabled")) return false;
  if (element.getAttribute("aria-hidden") === "true") return false;
  return element.tabIndex >= 0 || element.matches(FOCUSABLE_SELECTOR);
}

function focusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(isFocusable);
}

export function useModalFocusTrap<T extends HTMLElement>({
  ref,
  onClose,
}: {
  ref: RefObject<T | null>;
  onClose: () => void;
}) {
  useEffect(() => {
    if (typeof document === "undefined") return;
    const dialog = ref.current;
    if (!dialog) return;
    const dialogElement: HTMLElement = dialog;

    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const focusFirstInteractiveElement = () => {
      if (dialogElement.contains(document.activeElement)) return;
      const firstFocusable = focusableElements(dialogElement)[0];
      (firstFocusable ?? dialogElement).focus();
    };

    const frame = window.requestAnimationFrame(focusFirstInteractiveElement);

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const elements = focusableElements(dialogElement);
      if (!elements.length) {
        event.preventDefault();
        dialogElement.focus();
        return;
      }

      const first = elements[0];
      const last = elements[elements.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
        return;
      }

      if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKeyDown, true);
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [onClose, ref]);
}
