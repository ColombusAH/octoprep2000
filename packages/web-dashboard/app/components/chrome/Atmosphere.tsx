/**
 * Static broadcast-deck atmosphere — grid + vignette + scanlines.
 * No canvas, no intervals: cheap enough to stay mounted through a live recording.
 */
export function Atmosphere() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <div className="chrome-grid absolute inset-0" />
      <div className="chrome-vignette absolute inset-0" />
      <div className="chrome-scanlines absolute inset-0 opacity-70" />
    </div>
  );
}
