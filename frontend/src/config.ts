// Use the development URL for local testing, or the production URL in deployment.
// Assuming Django backend runs on localhost:8000
const IS_DEV = import.meta.env.DEV;

export const API_BASE_URL = IS_DEV 
  ? `http://${window.location.hostname}:8000/api`
  : 'https://live-wedding-gallery.onrender.com/api';

export const WS_BASE_URL = IS_DEV
  ? `ws://${window.location.hostname}:8000/ws`
  : 'wss://live-wedding-gallery.onrender.com/ws';

// Hardcoded slug for this specific wedding
export const WEDDING_SLUG = 'sandeep-prathyusha';
