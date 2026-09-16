import { useState, useEffect } from "react";
import { Loader2, Trash2 } from "lucide-react";
import PhotoLightbox from "../../components/PhotoLightbox";
import { API_BASE_URL, WS_BASE_URL, WEDDING_SLUG } from "../../config";

interface Photo {
  id: number;
  url: string;
  secure_url?: string;
  thumbnail_url?: string;
  aspect?: string;
  category?: string;
}

export default function AdminGallery() {
  const [activeTab, setActiveTab] = useState("All");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  
  const tabs = [
    "All",
    "Engagement",
    "Bride & Groom",
    "Pre-wedding Shoot",
    "Haldi",
    "Before Wedding Rituals",
    "Wedding Day",
    "Uncategorized"
  ];

  useEffect(() => {
    const fetchPhotos = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          const mappedPhotos = data.map((p: any) => ({
            id: p.id,
            url: p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: p.folder || "Uncategorized"
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
            category: p.folder || "Uncategorized"
          }));
          setPhotos(mappedPhotos);
        }
      } catch (_) {}
    }, 5000);

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
            category: p.folder || "Uncategorized"
          };
          setPhotos((prev) => {
            if (prev.find(x => x.id === newPhoto.id)) return prev;
            return [newPhoto, ...prev];
          });
        } else if (data.type === 'delete_photo') {
          setPhotos(prev => prev.filter(p => p.id !== data.photo_id));
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

  const deletePhoto = async (id: number) => {
    // Optimistic UI update
    setPhotos(prev => prev.filter(p => p.id !== id));
    
    // API Call
    try {
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/${id}/`, {
        method: "DELETE"
      });
      if (!res.ok) {
        console.error("Failed to delete photo on backend");
        // We could theoretically rollback here, but websocket polling will fix it shortly anyway if it failed
      }
    } catch (err) {
      console.error("Delete request failed", err);
    }
  };

  const filteredPhotos = activeTab === "All" ? photos : photos.filter(p => p.category === activeTab);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white uppercase tracking-wider">Manage Photos</h1>
        <p className="text-neutral-400 mt-2">View and manage all uploaded photos for the live gallery.</p>
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
                  ? "bg-rose-500 text-white font-medium" 
                  : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      
      {/* Masonry Grid */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
        </div>
      ) : filteredPhotos.length === 0 ? (
        <div className="text-center py-20 text-neutral-500">
          No photos found for this category yet.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredPhotos.map((photo, index) => (
            <div 
              key={photo.id} 
              className="group relative rounded-xl overflow-hidden shadow-sm bg-neutral-900 border border-neutral-800"
            >
              <div 
                className="cursor-pointer"
                onClick={() => openLightbox(index)}
              >
                <img 
                  src={photo.thumbnail_url || photo.url} 
                  alt={photo.category} 
                  className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
                  style={{ 
                    aspectRatio: photo.aspect?.replace('aspect-[', '').replace(']', '') || 'auto'
                  }}
                />
              </div>
              
              {/* Overlay with Delete Button */}
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none flex items-start justify-end p-2">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    deletePhoto(photo.id);
                  }}
                  className="p-2 bg-rose-500 text-white rounded-full hover:bg-rose-600 transition-colors pointer-events-auto shadow-lg"
                  title="Delete Photo"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {lightboxOpen && (
        <PhotoLightbox 
          photos={filteredPhotos} 
          initialIndex={currentPhotoIndex} 
          onClose={() => setLightboxOpen(false)} 
          onDelete={(id) => {
            deletePhoto(id);
            // Optionally close the lightbox if they deleted the very last photo?
            if (filteredPhotos.length <= 1) {
              setLightboxOpen(false);
            }
          }}
        />
      )}
    </div>
  );
}
