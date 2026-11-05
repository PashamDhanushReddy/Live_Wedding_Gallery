import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";
import { useWeddingRealtime } from "../../hooks/useWeddingRealtime";
import PhotoGridSkeleton from "../../components/ui/PhotoGridSkeleton";

// Dynamic import of PhotoLightbox to keep bundle size minimal
const PhotoLightbox = lazy(() => import("../../components/PhotoLightbox"));

interface Photo {
  id: number;
  url: string;
  secure_url?: string;
  thumbnail_url?: string;
  preview_url?: string;
  large_preview_url?: string;
  download_url?: string;
  aspect?: string;
  category?: string;
}

const mapPhoto = (p: any): Photo => ({
  id: p.id,
  url: p.large_preview_url || p.preview_url || p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
  secure_url: p.secure_url,
  thumbnail_url: p.thumbnail_url || p.preview_url || p.secure_url,
  preview_url: p.preview_url,
  large_preview_url: p.large_preview_url,
  download_url: p.download_url || p.secure_url || p.cloudinary_url,
  aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-[4/3]",
  category: p.folder || "Uncategorized"
});

export default function AdminGallery() {
  const [activeTab, setActiveTab] = useState("All");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const tabs = [
    "All",
    "Bride",
    "Groom",
    "Bride and Groom",
    "Engagement",
    "Pre-wedding Shoot",
    "Haldi",
    "Before Wedding Rituals",
    "Wedding Day",
    "Uncategorized"
  ];

  const fetchPhotos = useCallback(async () => {
    setLoading(true);
    try {
      const folderParam = activeTab !== "All" ? `?folder=${encodeURIComponent(activeTab)}` : "";
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/${folderParam}`);
      if (res.ok) {
        const data = await res.json();
        const rawList = Array.isArray(data) ? data : (data.results || []);
        const mappedPhotos = rawList.map(mapPhoto);
        setPhotos(mappedPhotos);
        setNextPageUrl(data.next || null);
      }
    } catch (err) {
      console.error("Failed to fetch photos", err);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchPhotos();
  }, [fetchPhotos]);

  const loadMorePhotos = async () => {
    if (!nextPageUrl || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await fetch(nextPageUrl);
      if (res.ok) {
        const data = await res.json();
        const rawList = Array.isArray(data) ? data : (data.results || []);
        const mappedPhotos = rawList.map(mapPhoto);
        setPhotos(prev => {
          const existingIds = new Set(prev.map((p: Photo) => p.id));
          const newItems = mappedPhotos.filter((p: Photo) => !existingIds.has(p.id));
          return [...prev, ...newItems];
        });
        setNextPageUrl(data.next || null);
      }
    } catch (err) {
      console.error("Failed to load more photos", err);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleNewPhotos = useCallback((newItems: Photo[]) => {
    setPhotos(prev => {
      const existingIds = new Set(prev.map((p: Photo) => p.id));
      const fresh = newItems.filter((p: Photo) => !existingIds.has(p.id));
      if (fresh.length === 0) return prev;
      return [...fresh, ...prev];
    });
  }, []);

  const handleDeletePhoto = useCallback((photoId: number) => {
    setPhotos(prev => prev.filter(p => p.id !== photoId));
  }, []);

  useWeddingRealtime<Photo>({
    slug: WEDDING_SLUG,
    activeTab,
    mapPhoto,
    onNewPhotos: handleNewPhotos,
    onDeletePhoto: handleDeletePhoto,
    onTotalCountChange: () => {},
  });

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  };

  const deletePhoto = async (id: number) => {
    // Optimistic UI update
    setPhotos(prev => prev.filter(p => p.id !== id));
    
    // API Call
    try {
      const token = localStorage.getItem("photographer_token");
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/${id}/`, {
        method: "DELETE",
        headers: {
          "Authorization": `Token ${token}`
        }
      });
      if (!res.ok) {
        console.error("Failed to delete photo on backend");
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
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-full text-sm whitespace-nowrap transition-colors cursor-pointer ${
                activeTab === tab 
                  ? "bg-rose-500 text-white font-medium shadow-sm" 
                  : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      
      {/* Grid */}
      {loading ? (
        <PhotoGridSkeleton count={12} />
      ) : filteredPhotos.length === 0 ? (
        <div className="text-center py-20 text-neutral-500">
          No photos found for this category yet.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredPhotos.map((photo, index) => (
            <div 
              key={photo.id} 
              className="group relative rounded-xl overflow-hidden shadow-sm bg-neutral-900 border border-neutral-800 aspect-[4/3]"
            >
              <div 
                className="cursor-pointer w-full h-full"
                onClick={() => openLightbox(index)}
                role="button"
                tabIndex={0}
                aria-label={`View photo ${photo.id}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openLightbox(index);
                  }
                }}
              >
                <img 
                  src={photo.thumbnail_url || photo.preview_url || photo.url} 
                  alt={photo.category} 
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              
              {/* Overlay with Delete Button */}
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none flex items-start justify-end p-2">
                <button 
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    deletePhoto(photo.id);
                  }}
                  className="p-2 bg-rose-500 text-white rounded-full hover:bg-rose-600 transition-colors pointer-events-auto shadow-lg cursor-pointer"
                  title="Delete Photo"
                  aria-label={`Delete photo ${photo.id}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Load More Button */}
      {!loading && nextPageUrl && (
        <div className="flex justify-center mt-8">
          <button
            type="button"
            onClick={loadMorePhotos}
            disabled={loadingMore}
            className="px-6 py-2.5 rounded-full bg-neutral-800 border border-neutral-700 text-neutral-200 hover:bg-neutral-700 font-medium text-sm transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {loadingMore ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-rose-500" />
                Loading more...
              </>
            ) : (
              "Load More Photos"
            )}
          </button>
        </div>
      )}

      {/* Lazy-loaded Lightbox */}
      {lightboxOpen && (
        <Suspense fallback={null}>
          <PhotoLightbox 
            photos={filteredPhotos} 
            initialIndex={currentPhotoIndex} 
            onClose={() => setLightboxOpen(false)} 
            onDelete={deletePhoto}
          />
        </Suspense>
      )}
    </div>
  );
}
