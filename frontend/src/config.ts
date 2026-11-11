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

export const GALLERY_EVENT_FOLDERS: readonly string[] = [
  "Engagement",
  "Pre-wedding Shoot",
  "Haldi",
  "Before Wedding Rituals",
  "Wedding Day",
];

export const GALLERY_PERSON_CATEGORIES: readonly string[] = [
  "Bride",
  "Groom",
  "Bride and Groom",
];

export const GALLERY_TABS: readonly string[] = [
  "All",
  ...GALLERY_PERSON_CATEGORIES,
  ...GALLERY_EVENT_FOLDERS,
  "Uncategorized",
];
