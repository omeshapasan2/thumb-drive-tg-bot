'use client';

/**
 * ProgressBar — overall progress showing X/Y completed.
 * Single large stat number + bar, no three-card grid.
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
              ? 'hsl(38, 92%, 50%, 0.12)'
              : 'hsl(173, 80%, 40%, 0.12)',
            color: state === 'paused_ram'
              ? 'var(--c-accent-500)'
              : 'var(--c-dominant-400)',
          }}>
            {state === 'paused_ram' ? '⏸ Paused' : state === 'processing' ? '▶ Active' : state}
          </span>
        )}
      </div>

      {/* Single stat line: big number / total */}
      <div className="overall-stat-line">
        <span className="overall-stat-line__big" id="stat-completed">{processedCount}</span>
        <span className="overall-stat-line__sep">/</span>
        <span className="overall-stat-line__total" id="stat-total">{totalVideos}</span>
        <span className="overall-stat-line__label">
          {isActive ? `${remaining} remaining` : 'videos'}
        </span>
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
