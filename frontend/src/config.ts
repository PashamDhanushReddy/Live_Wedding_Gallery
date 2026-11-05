// Use environment variables if provided (Vite import.meta.env), otherwise fallback to standard defaults.
const IS_DEV = import.meta.env.DEV;

export const API_BASE_URL: string = 
  import.meta.env.VITE_API_BASE_URL || 
  (IS_DEV ? `http://${window.location.hostname}:8000/api` : 'https://live-wedding-gallery.onrender.com/api');

export const WS_BASE_URL: string = 
  import.meta.env.VITE_WS_BASE_URL || 
  (IS_DEV ? `ws://${window.location.hostname}:8000/ws` : 'wss://live-wedding-gallery.onrender.com/ws');

// Wedding slug dynamically configurable or defaults to Sandeep & Prathyusha
export const WEDDING_SLUG: string = 
  import.meta.env.VITE_WEDDING_SLUG || 'sandeep-prathyusha';
