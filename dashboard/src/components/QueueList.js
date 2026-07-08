'use client';

/**
 * QueueList — scrollable list of pending and recently completed videos.
 * Each item shows filename, size, position, and status dot.
 * Items animate in with staggered fade-slide effect.
 */
export default function QueueList({ pending = [], completed = [] }) {
  const hasPending = pending.length > 0;
  const hasCompleted = completed.length > 0;

  if (!hasPending && !hasCompleted) {
    return (
      <div className="card" id="queue-list-card">
        <div className="card__header">
          <span className="card__title">Video Queue</span>
        </div>
        <div className="empty-state">
          <div className="empty-state__icon">📋</div>
          <div className="empty-state__title">Queue is empty</div>
          <div className="empty-state__text">
            Send /process in the bot to start<br />processing videos from Google Drive
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" id="queue-list-card">
      {/* Pending Videos */}
      {hasPending && (
        <>
          <div className="card__header">
            <span className="card__title">Pending ({pending.length})</span>
            <span className="card__badge" style={{
              background: 'hsl(173, 80%, 40%, 0.12)',
              color: 'var(--c-dominant-400)',
            }}>
              Waiting
            </span>
          </div>
          <div className="queue-list">
            {pending.map((task, index) => (
              <div
                key={`pending-${task.filename}-${index}`}
                className="queue-item"
                style={{ animationDelay: `${index * 0.05}s` }}
                id={`queue-item-${index}`}
              >
                <div className="queue-item__number">{index + 1}</div>
                <div className="queue-item__info">
                  <div className="queue-item__name" title={task.filename}>
                    {task.filename}
                  </div>
                  <div className="queue-item__size">
                    {task.file_size_human || formatSize(task.file_size)}
                  </div>
                </div>
                <div className="queue-item__status-dot queue-item__status-dot--pending" />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Completed Videos */}
      {hasCompleted && (
        <>
          <div className="card__header" style={{ marginTop: hasPending ? 'var(--sp-3)' : '0' }}>
            <span className="card__title">Completed ({completed.length})</span>
            <span className="card__badge" style={{
              background: 'hsl(152, 69%, 40%, 0.12)',
              color: 'var(--c-success)',
            }}>
              Done
            </span>
          </div>
          <div className="queue-list">
            {completed.slice().reverse().map((task, index) => (
              <div
                key={`completed-${task.filename}-${index}`}
                className="queue-item"
                style={{
                  animationDelay: `${index * 0.05}s`,
                  opacity: 0.65,
                }}
              >
                <div className="queue-item__number" style={{
                  color: task.status === 'completed' ? 'var(--c-success)' : 'var(--c-error)',
                }}>
                  {task.status === 'completed' ? '✓' : '✗'}
                </div>
                <div className="queue-item__info">
                  <div className="queue-item__name" title={task.filename}>
                    {task.filename}
                  </div>
                  <div className="queue-item__size">
                    {task.file_size_human || formatSize(task.file_size)}
                    {task.error && ` · ${task.error}`}
                  </div>
                </div>
                <div className={`queue-item__status-dot queue-item__status-dot--${task.status}`} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function formatSize(bytes) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(1)} ${units[i]}`;
}
