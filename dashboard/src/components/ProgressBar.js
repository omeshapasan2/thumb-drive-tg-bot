'use client';

/**
 * ProgressBar — overall progress showing X of Y videos completed.
 * Features animated gradient bar and stat grid.
 */
export default function ProgressBar({
  processedCount = 0,
  totalVideos = 0,
  progressPercent = 0,
  state = 'idle',
}) {
  const isActive = state !== 'idle' && totalVideos > 0;
  const remaining = Math.max(totalVideos - processedCount, 0);

  return (
    <div className="card overall-progress" id="progress-card">
      <div className="card__header">
        <span className="card__title">Overall Progress</span>
        {isActive && (
          <span className="card__badge" style={{
            background: state === 'paused_ram'
              ? 'rgba(245, 158, 11, 0.15)'
              : 'rgba(108, 123, 255, 0.15)',
            color: state === 'paused_ram'
              ? 'var(--accent-amber)'
              : 'var(--accent-blue)',
          }}>
            {state === 'paused_ram' ? '⏸ Paused (RAM)' : state === 'processing' ? '▶ Active' : state}
          </span>
        )}
      </div>

      <div className="overall-stats">
        <div className="overall-stat">
          <div className="overall-stat__value" id="stat-completed">{processedCount}</div>
          <div className="overall-stat__label">Completed</div>
        </div>
        <div className="overall-stat">
          <div className="overall-stat__value" id="stat-remaining">{remaining}</div>
          <div className="overall-stat__label">Remaining</div>
        </div>
        <div className="overall-stat">
          <div className="overall-stat__value" id="stat-total">{totalVideos}</div>
          <div className="overall-stat__label">Total</div>
        </div>
      </div>

      <div className="progress">
        <div className="progress__bar-container">
          <div
            className={`progress__bar ${isActive && processedCount < totalVideos ? 'progress__bar--animated' : ''}`}
            style={{ width: `${Math.min(progressPercent, 100)}%` }}
            id="overall-progress-bar"
          />
        </div>
        <div className="progress__label">
          <span>
            {isActive
              ? `${processedCount} of ${totalVideos} videos`
              : 'No active batch'}
          </span>
          <span className="progress__percent">
            {isActive ? `${progressPercent.toFixed(1)}%` : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
