'use client';

/**
 * StatusCard — displays the currently processing video with
 * animated status indicator, file info, and phase badge.
 */
export default function StatusCard({ currentTask, state, ram }) {
  if (!currentTask || state === 'idle') {
    return (
      <div className={`card status-card status-card--idle`} id="status-card">
        <div className="card__header">
          <span className="card__title">Currently Processing</span>
        </div>
        <div className="status-idle">
          <div className="status-idle__icon">📭</div>
          <div className="status-idle__text">
            {state === 'idle'
              ? 'No videos are being processed'
              : 'Waiting for the next video...'}
          </div>
        </div>
      </div>
    );
  }

  const phaseConfig = {
    downloading: {
      icon: '📥',
      label: 'Downloading',
      className: 'status-phase--downloading',
    },
    generating_thumbnails: {
      icon: '📸',
      label: 'Generating Thumbnails',
      className: 'status-phase--generating',
    },
    uploading: {
      icon: '📤',
      label: 'Uploading',
      className: 'status-phase--uploading',
    },
    completed: {
      icon: '✅',
      label: 'Completed',
      className: 'status-phase--completed',
    },
    failed: {
      icon: '❌',
      label: 'Failed',
      className: 'status-phase--failed',
    },
    pending: {
      icon: '⏳',
      label: 'Pending',
      className: 'status-phase--downloading',
    },
  };

  const phase = phaseConfig[currentTask.status] || phaseConfig.pending;
  const progress = Math.min(Math.max(currentTask.progress || 0, 0), 100);

  let displaySpeed = currentTask.speed || '';
  if (ram?.net) {
    if (currentTask.status === 'downloading' && ram.net.recv_bps > 0) {
      displaySpeed = ram.net.download_speed;
    } else if (currentTask.status === 'uploading' && ram.net.sent_bps > 0) {
      displaySpeed = ram.net.upload_speed;
    }
  }

  return (
    <div className="card status-card status-card--processing" id="status-card">
      <div className="card__header">
        <span className="card__title">Currently Processing</span>
        <span className={`status-phase ${phase.className}`}>
          {phase.icon} {phase.label}
        </span>
      </div>

      <div className="status-filename" id="current-filename">
        {currentTask.filename}
      </div>

      <div className="status-details">
        <span>📦 {currentTask.file_size_human || '—'}</span>
        {displaySpeed && (
          <span>⚡ {displaySpeed}</span>
        )}
        {currentTask.status === 'generating_thumbnails' && (
          <span>📸 3 thumbnails</span>
        )}
      </div>

      <div className="progress" id="current-progress">
        <div className="progress__bar-container">
          <div
            className={`progress__bar ${progress < 100 ? 'progress__bar--animated' : ''}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="progress__label">
          <span>{phase.label}</span>
          <span className="progress__percent">{progress.toFixed(1)}%</span>
        </div>
      </div>

      {currentTask.error && (
        <div className="error-text">
          ⚠️ {currentTask.error}
        </div>
      )}
    </div>
  );
}
