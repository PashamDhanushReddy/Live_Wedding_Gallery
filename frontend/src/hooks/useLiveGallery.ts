import { useState, useEffect, useRef } from 'react';
import { Photo } from '@/components/Gallery';

export function useLiveGallery(weddingSlug: string, initialPhotos: Photo[], sessionId?: string | null) {
  const [photos, setPhotos] = useState<Photo[]>(initialPhotos);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Determine the appropriate websocket URL based on environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const channel = sessionId ? `guest_${sessionId}` : `weddings/${weddingSlug}`;
    const wsUrl = `${protocol}//${window.location.host}/ws/${channel}/`;

    const connect = () => {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log(`Connected to live photo feed: ${channel}`);
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.event_type === 'photo.created' && !sessionId) {
          setPhotos(prev => [data.photo, ...prev]);
        } 
        else if (data.event_type === 'photo.matched' && sessionId) {
          setPhotos(prev => {
            if (prev.find(p => p.id === data.photo.id)) return prev;
            return [data.photo, ...prev];
          });
        }
      };

      wsRef.current.onclose = () => {
        console.log('Disconnected. Reconnecting in 3s...');
        setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [weddingSlug, sessionId]);

  return photos;
}
