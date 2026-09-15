import { useState, useEffect } from "react";
import { Search, SlidersHorizontal, Grid, LayoutGrid, Loader2 } from "lucide-react";
import PhotoLightbox from "../components/PhotoLightbox";
import { API_BASE_URL, WS_BASE_URL, WEDDING_SLUG } from "../config";

interface Photo {
  id: number;
  url: string;
  secure_url?: string;
  thumbnail_url?: string;
  aspect?: string;
  category?: string;
}

export default function GalleryPage() {
  const [activeTab, setActiveTab] = useState("All");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  
  const tabs = ["All", "Ceremony", "Reception", "Family", "Friends", "Couple", "Candid"];

  useEffect(() => {
    // 1. Fetch initial photos
    const fetchPhotos = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          // Backend returns serializer data. Map it.
          const mappedPhotos = data.map((p: any) => ({
            id: p.id,
            url: p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: "All" // Placeholder since backend doesn't have categories yet
          }));
          setPhotos(mappedPhotos);
        }
      } catch (err) {
        console.error("Failed to fetch photos", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPhotos();

    // 2. Polling every 5 seconds for reliable real-time updates
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          const mappedPhotos = data.map((p: any) => ({
            id: p.id,
            url: p.secure_url || p.cloudinary_url || "",
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: "All"
          }));
          setPhotos(prev => {
            // Only update if count changed (new photos added)
            if (mappedPhotos.length !== prev.length) {
              return mappedPhotos;
            }
            return prev;
          });
        }
      } catch (_) {}
    }, 5000);

    // 3. WebSocket for instant push updates (bonus speed)
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_BASE_URL}/weddings/${WEDDING_SLUG}/`);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_photo') {
          const p = data.photo;
          const newPhoto = {
            id: p.id,
            url: p.secure_url || p.cloudinary_url,
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: "All"
          };
          setPhotos((prev) => {
            if (prev.find(x => x.id === newPhoto.id)) return prev;
            return [newPhoto, ...prev];
          });
        }
      };
    } catch (_) {}

    return () => {
      clearInterval(pollInterval);
      ws?.close();
    };

  }, []);

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  };

  return (
    <div className="container mx-auto px-4 md:px-8 py-12 max-w-7xl">
      {/* Header section */}
      <div className="text-center mb-12">
        <p className="text-xs font-semibold tracking-[0.2em] text-muted-foreground uppercase mb-4">
          The Wedding Of
        </p>
        <h1 className="text-4xl md:text-5xl font-serif text-foreground mb-4">
          Sandeep Reddy & Prathyusha
        </h1>
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span>November 21, 2026</span>
          <span className="w-1 h-1 rounded-full bg-border"></span>
          <span>Hyderabad, Telangana</span>
        </div>
        
        <div className="mt-8 flex items-center justify-center gap-3">
          <div className="flex items-center gap-2 bg-secondary px-3 py-1 rounded-full text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            LIVE
          </div>
          <p className="text-sm">
            <strong className="text-foreground">{photos.length}</strong> photos and counting...
          </p>
        </div>
      </div>
      
      {/* Filters and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div className="flex overflow-x-auto pb-2 md:pb-0 hide-scrollbar gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-full text-sm whitespace-nowrap transition-colors ${
                activeTab === tab 
                  ? "bg-primary text-primary-foreground font-medium" 
                  : "bg-secondary text-foreground hover:bg-secondary/80"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        
        <div className="flex items-center gap-3 self-end md:self-auto">
          <button className="p-2.5 text-foreground hover:bg-secondary rounded-full transition-colors border border-border">
            <Search className="w-4 h-4" />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium border border-border hover:bg-secondary rounded-full transition-colors">
            <SlidersHorizontal className="w-4 h-4" />
            Sort
          </button>
          <div className="flex items-center p-1 bg-secondary rounded-full border border-border">
            <button className="p-1.5 bg-primary text-primary-foreground rounded-full shadow-sm">
              <Grid className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground">
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Masonry Grid */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : photos.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          No photos found for this event yet.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {photos.map((photo, index) => (
            <div 
              key={photo.id} 
              onClick={() => openLightbox(index)}
              className="cursor-pointer group relative rounded-xl overflow-hidden shadow-sm"
            >
              <img 
                src={photo.thumbnail_url || photo.url} 
                alt={photo.category} 
                className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
                style={{ 
                  aspectRatio: photo.aspect?.replace('aspect-[', '').replace(']', '') || 'auto'
                }}
              />
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                <p className="text-white font-medium">View Photo</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {lightboxOpen && (
        <PhotoLightbox 
          photos={photos} 
          initialIndex={currentPhotoIndex} 
          onClose={() => setLightboxOpen(false)} 
        />
      )}
    </div>
  );
}
