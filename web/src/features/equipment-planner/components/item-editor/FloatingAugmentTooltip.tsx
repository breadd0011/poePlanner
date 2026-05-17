import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { createPortal } from "react-dom";
import type { PlannerAugment } from "../../../../types";
import { AugmentTooltipPreview } from "./AugmentTooltipPreview";

export type FloatingAugmentTooltipState = {
  augment: PlannerAugment;
  id: string;
  top: number;
  left: number;
};

export function augmentTooltipId(value: string): string {
  return `augment-tooltip-${value.replace(/[^a-zA-Z0-9_-]+/g, "-")}`;
}

function clamp(value: number, min: number, max: number): number {
  if (max < min) return min;
  return Math.min(Math.max(value, min), max);
}

function floatingTooltipPosition(rect: DOMRect): Pick<FloatingAugmentTooltipState, "top" | "left"> {
  const gap = 12;
  const viewportPadding = 12;
  const tooltipWidth = Math.min(360, window.innerWidth - viewportPadding * 2);
  const tooltipHeightEstimate = Math.min(520, window.innerHeight - viewportPadding * 2);
  const maxLeft = window.innerWidth - tooltipWidth - viewportPadding;
  const maxTop = window.innerHeight - tooltipHeightEstimate - viewportPadding;

  const canOpenRight = rect.right + gap + tooltipWidth <= window.innerWidth - viewportPadding;
  const canOpenLeft = rect.left - gap - tooltipWidth >= viewportPadding;
  const preferredLeft = canOpenRight
    ? rect.right + gap
    : canOpenLeft
      ? rect.left - gap - tooltipWidth
      : rect.left;

  const preferredTop =
    rect.top + tooltipHeightEstimate <= window.innerHeight - viewportPadding
      ? rect.top - 8
      : window.innerHeight - tooltipHeightEstimate - viewportPadding;

  return {
    left: clamp(preferredLeft, viewportPadding, maxLeft),
    top: clamp(preferredTop, viewportPadding, maxTop),
  };
}

function tooltipStyle(state: FloatingAugmentTooltipState): CSSProperties {
  return {
    left: `${state.left}px`,
    top: `${state.top}px`,
  };
}

export function useFloatingAugmentTooltip() {
  const [state, setState] = useState<FloatingAugmentTooltipState | null>(null);
  const showTimerRef = useRef<number | null>(null);

  function clearShowTimer() {
    if (showTimerRef.current === null) return;
    window.clearTimeout(showTimerRef.current);
    showTimerRef.current = null;
  }

  useEffect(() => {
    return clearShowTimer;
  }, []);

  useEffect(() => {
    if (!state) return undefined;
    const hide = () => {
      clearShowTimer();
      setState(null);
    };
    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", hide);
    return () => {
      window.removeEventListener("scroll", hide, true);
      window.removeEventListener("resize", hide);
    };
  }, [state]);

  return {
    state,
    show(
      augment: PlannerAugment | null | undefined,
      id: string | undefined,
      target: HTMLElement,
    ) {
      clearShowTimer();
      if (!augment || !id) return;
      const rect = target.getBoundingClientRect();
      showTimerRef.current = window.setTimeout(() => {
        setState({ augment, id, ...floatingTooltipPosition(rect) });
        showTimerRef.current = null;
      }, 90);
    },
    hide() {
      clearShowTimer();
      setState(null);
    },
  };
}

export function FloatingAugmentTooltip({
  state,
}: {
  state: FloatingAugmentTooltipState | null;
}) {
  if (!state) return null;

  return createPortal(
    <div
      className="floating-augment-tooltip"
      id={state.id}
      role="tooltip"
      style={tooltipStyle(state)}
    >
      <AugmentTooltipPreview augment={state.augment} compact />
    </div>,
    document.body,
  );
}
