import type { FocusEvent, MouseEvent } from "react";
import type { PlannerAugment } from "../../../../types";
import { ItemIcon } from "./ItemIcon";
import {
  augmentTooltipId,
  FloatingAugmentTooltip,
  useFloatingAugmentTooltip,
} from "./FloatingAugmentTooltip";
import { iconToWebPath } from "./itemPresentation";

export function socketPatternClass(socketCapacity: number): string {
  if (socketCapacity <= 1) return "socketed-item-sockets--single";
  if (socketCapacity === 2) return "socketed-item-sockets--vertical";
  if (socketCapacity === 3) return "socketed-item-sockets--three";
  if (socketCapacity === 4) return "socketed-item-sockets--square";
  if (socketCapacity === 5) return "socketed-item-sockets--five";
  return "socketed-item-sockets--six";
}

function socketLayerClass(
  capacity: number,
  socketAugments: Array<PlannerAugment | null | undefined>,
): string {
  const interactive = socketAugments.some(Boolean);
  return [
    "socketed-item-sockets",
    socketPatternClass(capacity),
    interactive ? "socketed-item-sockets--interactive" : "",
  ]
    .filter(Boolean)
    .join(" ");
}

export function SocketLayer({
  socketCapacity,
  socketFilledCount,
  socketAugments = [],
}: {
  socketCapacity: number;
  socketFilledCount: number;
  socketAugments?: Array<PlannerAugment | null | undefined>;
}) {
  const capacity = Math.max(0, socketCapacity);
  const floatingTooltip = useFloatingAugmentTooltip();
  if (capacity <= 0) return null;

  function showSocketTooltip(
    event: MouseEvent<HTMLElement> | FocusEvent<HTMLElement>,
    augment: PlannerAugment | null | undefined,
    index: number,
  ) {
    floatingTooltip.show(
      augment,
      augment ? augmentTooltipId(`socket-${augment.id}-${index}`) : undefined,
      event.currentTarget,
    );
  }

  return (
    <>
      <div className={socketLayerClass(capacity, socketAugments)}>
        {Array.from({ length: capacity }).map((_, index) => {
          const isFilled = index < socketFilledCount;
          const augment = isFilled ? socketAugments[index] : null;

          return (
            <i
              aria-hidden={augment ? undefined : true}
              aria-describedby={augment ? augmentTooltipId(`socket-${augment.id}-${index}`) : undefined}
              aria-label={augment ? `${augment.name} socketed augment` : undefined}
              className={isFilled ? "filled" : ""}
              key={`item-socket-preview:${index}`}
              onBlur={floatingTooltip.hide}
              onFocus={(event) => showSocketTooltip(event, augment, index)}
              onMouseEnter={(event) => showSocketTooltip(event, augment, index)}
              onMouseLeave={floatingTooltip.hide}
              tabIndex={augment ? 0 : undefined}
            >
              {isFilled ? <span className="socketed-item-socket-fill" /> : null}
            </i>
          );
        })}
      </div>
      <FloatingAugmentTooltip state={floatingTooltip.state} />
    </>
  );
}

export function SocketedItemArtwork({
  iconPath,
  label,
  socketCapacity,
  socketFilledCount,
  socketAugments = [],
  className = "",
}: {
  iconPath: string | null;
  label: string;
  socketCapacity: number;
  socketFilledCount: number;
  socketAugments?: Array<PlannerAugment | null | undefined>;
  className?: string;
}) {
  return (
    <div className={`socketed-item-artwork ${className}`.trim()}>
      <ItemIcon
        label={label.slice(0, 2).toUpperCase()}
        iconPath={iconToWebPath(iconPath)}
      />
      <SocketLayer
        socketCapacity={socketCapacity}
        socketFilledCount={socketFilledCount}
        socketAugments={socketAugments}
      />
    </div>
  );
}
