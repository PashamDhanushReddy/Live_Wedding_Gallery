import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE_URL, WS_BASE_URL } from '../config';

export type RealtimeStatus = 'connecting' | 'connected' | 'disconnected' | 'fallback';

export interface UseWeddingRealtimeOptions<T> {
  slug: string;
  activeTab: string;
  mapPhoto: (raw: any) => T;
  onNewPhotos: (photos: T[]) => void;
  onDeletePhoto: (photoId: number) => void;
  onTotalCountChange: (updater: (prev: number) => number) => void;
}

export function useWeddingRealtime<T extends { id: number; category?: string }>({
  slug,
  activeTab,
  mapPhoto,
  onNewPhotos,
  onDeletePhoto,
  onTotalCountChange,
}: UseWeddingRealtimeOptions<T>) {
  const [connectionStatus, setConnectionStatus] = useState<RealtimeStatus>('connecting');
  const [lastSyncTime, setLastSyncTime] = useState<Date>(new Date());

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pongTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallbackPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const debounceFetchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Deduplication tracking sets
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const seenPhotoIdsRef = useRef<Set<number>>(new Set());

  // Keep latest options in ref to avoid re-triggering connection on tab changes
  const optionsRef = useRef({
    slug,
    activeTab,
    mapPhoto,
    onNewPhotos,
    onDeletePhoto,
    onTotalCountChange,
  });

  useEffect(() => {
    optionsRef.current = {
      slug,
      activeTab,
      mapPhoto,
      onNewPhotos,
      onDeletePhoto,
      onTotalCountChange,
    };
  }, [slug, activeTab, mapPhoto, onNewPhotos, onDeletePhoto, onTotalCountChange]);

  // Clean, debounced fetch of latest photos via paginated API
  const fetchLatestPage = useCallback(async () => {
    try {
      const currentTab = optionsRef.current.activeTab;
      const folderParam = currentTab !== 'All' ? `?folder=${encodeURIComponent(currentTab)}` : '';
      const url = `${API_BASE_URL}/weddings/${optionsRef.current.slug}/photos/${folderParam}`;

      const res = await fetch(url);
      if (!res.ok) return;

      const data = await res.json();
      const rawList = Array.isArray(data) ? data : (data.results || []);
      const mapped = rawList.map(optionsRef.current.mapPhoto);

      // Track photo IDs to prevent future duplicate fetches
      mapped.forEach((p: T) => seenPhotoIdsRef.current.add(p.id));

      if (data.count !== undefined && data.count !== null) {
        optionsRef.current.onTotalCountChange(() => data.count);
      }

      optionsRef.current.onNewPhotos(mapped);
      setLastSyncTime(new Date());
    } catch (err) {
      console.warn('[Realtime] Failed to sync latest page from paginated API:', err);
    }
  }, []);

  // Debounced queue trigger for burst photo uploads
  const triggerDebouncedSync = useCallback(() => {
    if (debounceFetchTimerRef.current) {
      clearTimeout(debounceFetchTimerRef.current);
    }
    // 350ms debounce bundles multi-photo bursts into 1 paginated API call
    debounceFetchTimerRef.current = setTimeout(() => {
      fetchLatestPage();
    }, 350);
  }, [fetchLatestPage]);

  // Fallback polling: strictly used ONLY when WebSocket is unavailable
  const startFallbackPolling = useCallback(() => {
    if (fallbackPollTimerRef.current) return;
    console.info('[Realtime] Activating gentle fallback polling (every 35s)');
    setConnectionStatus('fallback');

    fallbackPollTimerRef.current = setInterval(() => {
      // Only poll if document is visible to respect battery and bandwidth
      if (document.visibilityState === 'visible') {
        fetchLatestPage();
      }
    }, 35000);
  }, [fetchLatestPage]);

  const stopFallbackPolling = useCallback(() => {
    if (fallbackPollTimerRef.current) {
      clearInterval(fallbackPollTimerRef.current);
      fallbackPollTimerRef.current = null;
    }
  }, []);

  // WebSocket connect implementation
  const connectWebSocket = useCallback(() => {
    // Clear any existing socket
    if (wsRef.current) {
      try {
        wsRef.current.close(1000);
      } catch (_) {}
      wsRef.current = null;
    }

    const currentSlug = optionsRef.current.slug;
    const wsUrl = `${WS_BASE_URL}/weddings/${currentSlug}/`;

    setConnectionStatus('connecting');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.info(`[Realtime] WebSocket connected for wedding: ${currentSlug}`);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        stopFallbackPolling();

        // Start heartbeat ping
        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'ping' }));
              // Expect pong within 10 seconds
              if (pongTimeoutRef.current) clearTimeout(pongTimeoutRef.current);
              pongTimeoutRef.current = setTimeout(() => {
                console.warn('[Realtime] Heartbeat pong timeout. Reconnecting...');
                ws.close(4000);
              }, 10000);
            } catch (_) {}
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Heartbeat pong
          if (data.type === 'pong') {
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current);
              pongTimeoutRef.current = null;
            }
            return;
          }

          if (data.type === 'connection_established') {
            return;
          }

          // Duplicate event detection
          if (data.event_id) {
            if (seenEventIdsRef.current.has(data.event_id)) {
              return;
            }
            seenEventIdsRef.current.add(data.event_id);
            // Cap seen set to prevent memory growth
            if (seenEventIdsRef.current.size > 2000) {
              const iter = seenEventIdsRef.current.values();
              for (let i = 0; i < 500; i++) {
                const val = iter.next().value;
                if (val !== undefined) {
                  seenEventIdsRef.current.delete(val);
                }
              }
            }
          }

          // Handle lightweight new_photo event
          if (data.type === 'new_photo') {
            const photoId = Number(data.photo_id);
            if (photoId && seenPhotoIdsRef.current.has(photoId)) {
              return;
            }
            if (photoId) {
              seenPhotoIdsRef.current.add(photoId);
            }

            // Immediately increment total photo counter
            optionsRef.current.onTotalCountChange((prev) => prev + 1);

            // Fetch actual photo metadata using the paginated API
            const currentTab = optionsRef.current.activeTab;
            if (currentTab === 'All' || !data.folder || data.folder === currentTab) {
              triggerDebouncedSync();
            }
          } else if (data.type === 'delete_photo') {
            const photoId = Number(data.photo_id);
            if (photoId) {
              seenPhotoIdsRef.current.delete(photoId);
              optionsRef.current.onDeletePhoto(photoId);
              optionsRef.current.onTotalCountChange((prev) => Math.max(0, prev - 1));
            }
          }
        } catch (err) {
          console.warn('[Realtime] Error processing WebSocket message:', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('[Realtime] WebSocket error:', err);
      };

      ws.onclose = (event) => {
        console.warn(`[Realtime] WebSocket closed (code=${event.code})`);
        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        if (pongTimeoutRef.current) clearTimeout(pongTimeoutRef.current);

        // If closed intentionally, do not reconnect
        if (event.code === 1000) {
          setConnectionStatus('disconnected');
          return;
        }

        // Reconnect with exponential backoff + jitter
        reconnectAttemptsRef.current += 1;
        const attempts = reconnectAttemptsRef.current;

        if (attempts > 5) {
          // Switch to fallback mode after repeated failures
          startFallbackPolling();
        } else {
          setConnectionStatus('disconnected');
        }

        const backoffMs = Math.min(1000 * Math.pow(1.5, attempts), 15000) + Math.random() * 500;
        console.info(`[Realtime] Scheduling reconnect attempt #${attempts} in ${Math.round(backoffMs)}ms`);

        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          connectWebSocket();
        }, backoffMs);
      };
    } catch (e) {
      console.warn('[Realtime] Failed to initialize WebSocket:', e);
      startFallbackPolling();
    }
  }, [stopFallbackPolling, startFallbackPolling, triggerDebouncedSync]);

  // Initial connection setup & cleanup
  useEffect(() => {
    connectWebSocket();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Tab reopened: if socket is closed or in fallback, trigger immediate sync & attempt reconnect
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          fetchLatestPage();
          connectWebSocket();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (pongTimeoutRef.current) clearTimeout(pongTimeoutRef.current);
      if (debounceFetchTimerRef.current) clearTimeout(debounceFetchTimerRef.current);
      stopFallbackPolling();
    };
  }, [connectWebSocket, stopFallbackPolling, fetchLatestPage]);

  return {
    connectionStatus,
    isLive: connectionStatus === 'connected',
    lastSyncTime,
    refresh: fetchLatestPage,
  };
}
