'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useWebSocket — custom hook for managing the WebSocket connection
 * to the bot's FastAPI server.
 *
 * Features:
 * - Auto-reconnect with exponential backoff
 * - Connection state tracking
 * - Ping/pong keep-alive
 * - Parses incoming JSON and updates React state
 */

const INITIAL_RECONNECT_DELAY = 1000;  // 1 second
const MAX_RECONNECT_DELAY = 30000;     // 30 seconds
const PING_INTERVAL = 25000;           // 25 seconds

export function useWebSocket() {
  const [status, setStatus] = useState(null);
  const [ram, setRam] = useState(null);
  const [connectionState, setConnectionState] = useState('disconnected');

  const wsRef = useRef(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);

  const getWebSocketUrl = useCallback(() => {
    if (typeof window === 'undefined') return null;

    // Use environment variable or derive from page URL
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (wsUrl) {
      // Convert http(s) to ws(s)
      return wsUrl.replace(/^http/, 'ws') + '/ws';
    }

    // Default: connect to same host on port 8765
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    return `${protocol}//${host}:8765/ws`;
  }, []);

  const handleMessage = useCallback((event) => {
    try {
      const msg = JSON.parse(event.data);

      if (msg.type === 'initial_state' || msg.type === 'queue_update') {
        if (msg.data) {
          setStatus(msg.data);
        }
        if (msg.ram) {
          setRam(msg.ram);
        }
      } else if (msg.type === 'pong') {
        // Keep-alive response, no action needed
      }
    } catch (e) {
      console.warn('[WS] Failed to parse message:', e);
    }
  }, []);

  const startPing = useCallback(() => {
    stopPing();
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL);
  }, []);

  const stopPing = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    const url = getWebSocketUrl();
    if (!url) return;

    // Cleanup existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    setConnectionState('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to', url);
        setConnectionState('connected');
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        startPing();
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        setConnectionState('disconnected');
        stopPing();
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.warn('[WS] Error:', error);
        // onclose will fire after this
      };
    } catch (error) {
      console.error('[WS] Failed to connect:', error);
      setConnectionState('disconnected');
      scheduleReconnect();
    }
  }, [getWebSocketUrl, handleMessage, startPing, stopPing]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    const delay = reconnectDelayRef.current;
    console.log(`[WS] Reconnecting in ${delay}ms...`);

    reconnectTimeoutRef.current = setTimeout(() => {
      // Exponential backoff
      reconnectDelayRef.current = Math.min(
        reconnectDelayRef.current * 1.5,
        MAX_RECONNECT_DELAY
      );
      connect();
    }, delay);
  }, [connect]);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      stopPing();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, stopPing]);

  return {
    status,
    ram,
    connectionState,
  };
}
