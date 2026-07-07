'use client';

import { useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import StatusCard from '../components/StatusCard';
import QueueList from '../components/QueueList';
import ProgressBar from '../components/ProgressBar';
import RamMonitor from '../components/RamMonitor';

export default function DashboardPage() {
  const { status, ram, connectionState } = useWebSocket();

  // Initialize Telegram Web App
  useEffect(() => {
    if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
      // Apply Telegram theme
      tg.setHeaderColor('#0f0f1a');
      tg.setBackgroundColor('#0f0f1a');
    }
  }, []);

  const connectionBadgeClass = {
    connected: 'connection-badge connection-badge--connected',
    connecting: 'connection-badge connection-badge--connecting',
    disconnected: 'connection-badge connection-badge--disconnected',
  }[connectionState] || 'connection-badge connection-badge--disconnected';

  const connectionLabel = {
    connected: 'Live',
    connecting: 'Connecting...',
    disconnected: 'Offline',
  }[connectionState] || 'Offline';

  return (
    <main className="dashboard" id="dashboard-root">
      {/* Header */}
      <header className="header" id="dashboard-header">
        <h1 className="header__title">Video Thumbnail Bot</h1>
        <p className="header__subtitle">Processing Dashboard</p>
        <div className={connectionBadgeClass}>
          <span className="connection-dot" />
          {connectionLabel}
        </div>
      </header>

      {/* Overall Progress */}
      <section id="overall-progress-section">
        <ProgressBar
          processedCount={status?.processed_count || 0}
          totalVideos={status?.total_videos || 0}
          progressPercent={status?.progress_percent || 0}
          state={status?.state || 'idle'}
        />
      </section>

      {/* Current Video Status */}
      <section id="status-card-section">
        <StatusCard
          currentTask={status?.current_task || null}
          state={status?.state || 'idle'}
        />
      </section>

      {/* Queue List */}
      <section id="queue-list-section">
        <QueueList
          pending={status?.pending || []}
          completed={status?.completed || []}
        />
      </section>

      {/* RAM Monitor */}
      <section id="ram-monitor-section">
        <RamMonitor ram={ram} />
      </section>
    </main>
  );
}
