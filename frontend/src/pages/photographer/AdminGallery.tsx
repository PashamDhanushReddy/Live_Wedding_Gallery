import { useState, useEffect, useCallback, useRef, lazy, Suspense } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Trash2, AlertCircle, RefreshCw } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG, GALLERY_TABS } from "../../config";
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

const PHOTOGRAPHER_PAGE_SIZE = 50;

const normalizeApiUrl = (url: string | null | undefined): string | null => {
  if (!url) return null;
  if (API_BASE_URL.startsWith("https://") && url.startsWith("http://")) {
    return `https://${url.slice("http://".length)}`;
  }
  return url;
};

const mapPhoto = (p: any): Photo => ({
  id: p.id,
  url: p.large_preview_url || p.preview_url || p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
  secure_url: p.secure_url,
  thumbnail_url: p.thumbnail_url || p.preview_url || p.secure_url,
  preview_url: p.preview_url,
  large_preview_url: p.large_preview_url,
  download_url: p.download_url || p.secure_url || p.cloudinary_url,
  aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-[4/3]",
  category: p.folder || p.ai_category || "Uncategorized"
});

interface PhotoPageResult {
  photos: Photo[];
  next: string | null;
  count: number | null;
  error?: string;
  unauthorized?: boolean;
}

export default function AdminGallery() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("All");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);

  const tabs = GALLERY_TABS;

  const requestPhotoPage = useCallback(async (url: string): Promise<PhotoPageResult> => {
    const token = localStorage.getItem("photographer_token");
    if (!token) {
      navigate("/photographer/login", { replace: true });
      return { photos: [], next: null, count: null, unauthorized: true };
    }

    const res = await fetch(url, {
      headers: {
        "Authorization": `Token ${token}`
      }
    });

    if (res.status === 401) {
      localStorage.removeItem("photographer_token");
      navigate("/photographer/login", { replace: true });
      return { photos: [], next: null, count: null, unauthorized: true };
    }

    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const msg =
        data?.message ||
        data?.detail ||
        data?.error ||
        `Unable to load photos (HTTP ${res.status}).`;
      return { photos: [], next: null, count: null, error: msg };
    }

    const rawList = Array.isArray(data) ? data : (data?.results || []);
    return {
      photos: rawList.map(mapPhoto),
      next: normalizeApiUrl(data?.next),
      count: typeof data?.count === "number" ? data.count : null,
    };
  }, [navigate]);

  const fetchPhotos = useCallback(async () => {
    const seq = ++requestSeqRef.current;
    setLoading(true);
    setLoadingMore(false);
    setLoadingAll(false);
    setError(null);
    try {
      const params = new URLSearchParams({
        page_size: String(PHOTOGRAPHER_PAGE_SIZE),
      });
      if (activeTab !== "All") {
        params.set("folder", activeTab);
      }
      const result = await requestPhotoPage(
        `${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/?${params.toString()}`
      );
      if (seq !== requestSeqRef.current || result.unauthorized) return;

      if (result.error) {
        setError(result.error);
        setPhotos([]);
        setNextPageUrl(null);
        setTotalCount(null);
        return;
      }

      setPhotos(result.photos);
      setNextPageUrl(result.next);
      setTotalCount(result.count ?? result.photos.length);
    } catch (err) {
      if (seq !== requestSeqRef.current) return;
      console.error("Failed to fetch photos", err);
      setError("Network error while loading photos. Please check your connection and try again.");
    } finally {
      if (seq === requestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [activeTab, requestPhotoPage]);

  useEffect(() => {
    fetchPhotos();
    return () => {
      // Cancel in-flight pagination loops on tab change or unmount
      requestSeqRef.current += 1;
    };
  }, [fetchPhotos]);

  const appendUniquePhotos = useCallback((incoming: Photo[]) => {
    setPhotos((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const newItems = incoming.filter((p) => !existingIds.has(p.id));
      return newItems.length > 0 ? [...prev, ...newItems] : prev;
    });
  }, []);

  const loadMorePhotos = async () => {
    if (!nextPageUrl || loadingMore || loadingAll) return;
    const seq = requestSeqRef.current;
    setLoadingMore(true);
    setError(null);
    try {
      const result = await requestPhotoPage(nextPageUrl);
      if (seq !== requestSeqRef.current || result.unauthorized) return;
      if (result.error) {
        setError(result.error);
        return;
      }
      appendUniquePhotos(result.photos);
      setNextPageUrl(result.next);
      if (result.count !== null) {
        setTotalCount(result.count);
      }
    } catch (err) {
      if (seq !== requestSeqRef.current) return;
      console.error("Failed to load more photos", err);
      setError("Network error while loading more photos.");
    } finally {
      if (seq === requestSeqRef.current) {
        setLoadingMore(false);
      }
    }
  };

  const loadAllPhotos = async () => {
    if (!nextPageUrl || loadingMore || loadingAll) return;
    const seq = requestSeqRef.current;
    setLoadingAll(true);
    setError(null);
    try {
      let cursorUrl: string | null = nextPageUrl;
      while (cursorUrl && seq === requestSeqRef.current) {
        const result = await requestPhotoPage(cursorUrl);
        if (seq !== requestSeqRef.current || result.unauthorized) return;
        if (result.error) {
          setError(result.error);
          return;
        }
        appendUniquePhotos(result.photos);
        cursorUrl = result.next;
        setNextPageUrl(cursorUrl);
        if (result.count !== null) {
          setTotalCount(result.count);
        }
      }
    } catch (err) {
      if (seq !== requestSeqRef.current) return;
      console.error("Failed to load all photos", err);
      setError("Network error while loading remaining photos.");
    } finally {
      if (seq === requestSeqRef.current) {
        setLoadingAll(false);
      }
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

  const handleTotalCountChange = useCallback((updater: (prev: number) => number) => {
    setTotalCount((prev) => updater(prev ?? 0));
  }, []);

  useWeddingRealtime<Photo>({
    slug: WEDDING_SLUG,
    activeTab,
    mapPhoto,
    onNewPhotos: handleNewPhotos,
    onDeletePhoto: handleDeletePhoto,
    onTotalCountChange: handleTotalCountChange,
    authToken: localStorage.getItem("photographer_token"),
  });

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  };

  const deletePhoto = async (id: number) => {
    // Optimistic UI update
    setPhotos(prev => prev.filter(p => p.id !== id));
    setTotalCount(prev => (prev !== null ? Math.max(0, prev - 1) : null));
    
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
        fetchPhotos();
      }
    } catch (err) {
      console.error("Delete request failed", err);
      fetchPhotos();
    }
  };

  // Backend handles folder + AI category filtering; avoid dropping AI-tagged photos client-side
  const filteredPhotos = photos;
  const remainingCount = totalCount !== null ? Math.max(0, totalCount - filteredPhotos.length) : null;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white uppercase tracking-wider">Manage Photos</h1>
          <p className="text-neutral-400 mt-2">View and manage all uploaded photos for the live gallery.</p>
        </div>

        {!loading && !error && (
          <div className="flex items-center gap-3 text-sm text-neutral-400">
            <span>
              Showing <span className="text-white font-semibold">{filteredPhotos.length}</span>
              {totalCount !== null ? (
                <> of <span className="text-white font-semibold">{totalCount}</span></>
              ) : null}{" "}
              photos
            </span>
            {nextPageUrl && (
              <button
                type="button"
                onClick={loadAllPhotos}
                disabled={loadingMore || loadingAll}
                className="px-3.5 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/40 text-rose-300 hover:bg-rose-500/25 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {loadingAll ? "Loading all..." : remainingCount ? `Load All (${remainingCount} more)` : "Load All"}
              </button>
            )}
          </div>
        )}
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

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/40 text-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm">{error}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={fetchPhotos}
              className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-white text-xs font-medium flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </button>
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem("photographer_token");
                navigate("/photographer/login", { replace: true });
              }}
              className="px-3 py-1.5 rounded-lg bg-rose-500 hover:bg-rose-600 text-white text-xs font-medium cursor-pointer"
            >
              Sign In Again
            </button>
          </div>
        </div>
      )}
      
      {/* Grid */}
      {loading ? (
        <PhotoGridSkeleton count={12} />
      ) : filteredPhotos.length === 0 ? (
        !error && (
          <div className="text-center py-20 text-neutral-500">
            No photos found for this category yet.
          </div>
        )
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

      {/* Pagination Controls */}
      {!loading && nextPageUrl && (
        <div className="flex flex-wrap justify-center gap-3 mt-8">
          <button
            type="button"
            onClick={loadMorePhotos}
            disabled={loadingMore || loadingAll}
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
          <button
            type="button"
            onClick={loadAllPhotos}
            disabled={loadingMore || loadingAll}
            className="px-6 py-2.5 rounded-full bg-rose-500 hover:bg-rose-600 text-white font-medium text-sm transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {loadingAll ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                Loading all photos...
              </>
            ) : (
              remainingCount ? `Load All Remaining (${remainingCount})` : "Load All Remaining"
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
