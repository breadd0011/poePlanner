import { useEffect, useState } from "react";

export function ItemIcon({
  label,
  iconPath,
  onImageLoad,
}: {
  label: string;
  iconPath: string | null;
  onImageLoad?: (image: HTMLImageElement) => void;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [iconPath]);
  if (iconPath && !failed) {
    return (
      <img
        className="item-icon-image"
        src={iconPath}
        alt=""
        onError={() => setFailed(true)}
        onLoad={(event) => onImageLoad?.(event.currentTarget)}
      />
    );
  }
  return <div className="item-icon-placeholder">{label}</div>;
}
