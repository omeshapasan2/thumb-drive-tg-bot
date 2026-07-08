'use client';

/**
 * RamMonitor — displays current RAM usage with a color-coded bar.
 * Green = OK, Amber = High, Red = Critical
 */
export default function RamMonitor({ ram }) {
  if (!ram) {
    return null;
  }

  const percent = ram.percent || 0;
  const status = ram.status || 'OK';

  const barClass = {
    OK: 'ram-monitor__bar--ok',
    HIGH: 'ram-monitor__bar--high',
    CRITICAL: 'ram-monitor__bar--critical',
  }[status] || 'ram-monitor__bar--ok';

  const emoji = {
    OK: '🟢',
    HIGH: '🟡',
    CRITICAL: '🔴',
  }[status] || '🟢';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
      <div className="ram-monitor" id="ram-monitor">
        <div className="ram-monitor__icon">{emoji}</div>
        <div className="ram-monitor__info">
          <div className="ram-monitor__label">
            RAM — {(ram.available_mb || 0).toFixed(0)} MB free
          </div>
          <div className="ram-monitor__bar-container">
            <div
              className={`ram-monitor__bar ${barClass}`}
              style={{ width: `${Math.min(percent, 100)}%` }}
            />
          </div>
        </div>
        <div className="ram-monitor__value">{percent.toFixed(0)}%</div>
      </div>

      {ram.net && (
        <div className="net-speed">
          <span>📥 Down: <strong>{ram.net.download_speed}</strong></span>
          <span>📤 Up: <strong>{ram.net.upload_speed}</strong></span>
        </div>
      )}
    </div>
  );
}
