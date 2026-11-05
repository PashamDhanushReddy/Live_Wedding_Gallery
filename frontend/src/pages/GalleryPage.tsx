import { useState, useEffect, useCallback, useRef, useMemo, lazy, Suspense } from "react";
import { Loader2, Calendar, MapPin, Heart, Grid, Crown, AlertCircle, RefreshCw, Search, X } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../config";
import { useWeddingRealtime } from "../hooks/useWeddingRealtime";
import { useDebounce } from "../hooks/useDebounce";
import GalleryPhotoCard, { type GalleryPhotoItem } from "../components/ui/GalleryPhotoCard";
import PhotoGridSkeleton from "../components/ui/PhotoGridSkeleton";

// Dynamic import of PhotoLightbox so yet-another-react-lightbox isn't in initial bundle
const PhotoLightbox = lazy(() => import("../components/PhotoLightbox"));

const mapPhoto = (p: any): GalleryPhotoItem => ({
  id: p.id,
  url: p.large_preview_url || p.preview_url || p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
  secure_url: p.secure_url,
  thumbnail_url: p.thumbnail_url || p.preview_url || p.secure_url,
  preview_url: p.preview_url,
  large_preview_url: p.large_preview_url,
  download_url: p.download_url || p.secure_url || p.cloudinary_url,
  aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-[4/3]",
  category: p.folder || "Uncategorized",
  width: p.width,
  height: p.height,
});

import bgImage from "../assets/bg_blue.png";
import mobileBg from "../assets/mobile_bg.png";

interface TabCacheEntry {
  photos: GalleryPhotoItem[];
  nextPageUrl: string | null;
  totalCount: number;
  timestamp: number;
}

export default function GalleryPage() {
  const [activeTab, setActiveTab] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 350);

  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<GalleryPhotoItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);

  // In-memory tab cache to avoid redundant API requests during tab switching (Requirement 10 & 16)
  const tabCacheRef = useRef<Map<string, TabCacheEntry>>(new Map());
  const inFlightAbortRef = useRef<AbortController | null>(null);

  const tabs = useMemo(() => [
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
  ], []);

  // Fetch photos for current category/folder and search query
  const fetchPhotos = useCallback(async (isInitial = false) => {
    const cacheKey = `${activeTab}__${debouncedSearch.trim()}`;

    // Serve from cache if available within 60s and not explicit retry
    if (!isInitial) {
      const cached = tabCacheRef.current.get(cacheKey);
      if (cached && (Date.now() - cached.timestamp < 60000)) {
        setPhotos(cached.photos);
        setNextPageUrl(cached.nextPageUrl);
        setTotalCount(cached.totalCount);
        setLoading(false);
        setError(null);
        return;
      }
    }

    // Cancel in-flight duplicate requests
    if (inFlightAbortRef.current) {
      inFlightAbortRef.current.abort();
    }
    const abortController = new AbortController();
    inFlightAbortRef.current = abortController;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (activeTab !== "All") params.append("folder", activeTab);
      if (debouncedSearch.trim()) params.append("q", debouncedSearch.trim());

      const queryStr = params.toString() ? `?${params.toString()}` : "";
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/${queryStr}`, {
        signal: abortController.signal
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: Failed to load photos.`);
      }

      const data = await res.json();
      const rawList = Array.isArray(data) ? data : (data.results || []);
      const mappedPhotos = rawList.map(mapPhoto);

      setPhotos(mappedPhotos);
      const computedCount = (data.count !== undefined && data.count !== null) ? data.count : mappedPhotos.length;
      setTotalCount(computedCount);
      setNextPageUrl(data.next || null);

      // Cache the result
      tabCacheRef.current.set(cacheKey, {
        photos: mappedPhotos,
        nextPageUrl: data.next || null,
        totalCount: computedCount,
        timestamp: Date.now(),
      });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      console.error("Failed to fetch gallery photos", err);
      setError(err.message || "Failed to load photos. Please check your network connection.");
    } finally {
      setLoading(false);
    }
  }, [activeTab, debouncedSearch]);

  useEffect(() => {
    fetchPhotos(false);
  }, [fetchPhotos]);

  // Load next cursor page
  const loadMorePhotos = useCallback(async () => {
    if (!nextPageUrl || loadingMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);

    try {
      const res = await fetch(nextPageUrl);
      if (!res.ok) {
        throw new Error(`Failed to load page: ${res.status}`);
      }
      const data = await res.json();
      const rawList = Array.isArray(data) ? data : (data.results || []);
      const mappedPhotos = rawList.map(mapPhoto);

      setPhotos(prev => {
        const existingIds = new Set(prev.map((p: GalleryPhotoItem) => p.id));
        const newItems = mappedPhotos.filter((p: GalleryPhotoItem) => !existingIds.has(p.id));
        const updated = [...prev, ...newItems];

        // Update tab cache with merged list
        const cacheKey = `${activeTab}__${debouncedSearch.trim()}`;
        const existingCache = tabCacheRef.current.get(cacheKey);
        if (existingCache) {
          existingCache.photos = updated;
          existingCache.nextPageUrl = data.next || null;
        }
        return updated;
      });

      setNextPageUrl(data.next || null);
    } catch (err: any) {
      console.error("Failed to load more photos", err);
      setLoadMoreError("Could not load additional photos. Click below to retry.");
    } finally {
      setLoadingMore(false);
    }
  }, [nextPageUrl, loadingMore, activeTab, debouncedSearch]);

  // Real-time synchronization via Django Channels WebSocket with fallback refresh
  const handleNewPhotos = useCallback((newItems: GalleryPhotoItem[]) => {
    setPhotos(prev => {
      const existingIds = new Set(prev.map(p => p.id));
      const fresh = newItems.filter(p => !existingIds.has(p.id));
      if (fresh.length === 0) return prev;
      return [...fresh, ...prev];
    });
    // Invalidate tab cache to ensure freshest data
    tabCacheRef.current.clear();
  }, []);

  const handleDeletePhoto = useCallback((photoId: number) => {
    setPhotos(prev => prev.filter(p => p.id !== photoId));
    tabCacheRef.current.clear();
  }, []);

  const { connectionStatus, isLive, refresh } = useWeddingRealtime<GalleryPhotoItem>({
    slug: WEDDING_SLUG,
    activeTab,
    mapPhoto,
    onNewPhotos: handleNewPhotos,
    onDeletePhoto: handleDeletePhoto,
    onTotalCountChange: setTotalCount,
  });

  const openLightbox = useCallback((index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxOpen(false);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#fffaf7] to-[#fcfaf8] pb-12">
      {/* Header Wrapper with Floral Background */}
      <div className="relative w-full z-10 pt-16 md:pt-24 pb-4">
        
        {/* Floral Background Image for Desktop */}
        <div 
          className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-50 -z-10 pointer-events-none [mask-image:linear-gradient(to_bottom,white_80%,transparent_100%)] hidden md:block"
          style={{ backgroundImage: `url(${bgImage})` }}
        />

        {/* Floral Background Image for Mobile */}
        <div 
          className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-50 -z-10 pointer-events-none [mask-image:linear-gradient(to_bottom,white_80%,transparent_100%)] md:hidden"
          style={{ backgroundImage: `url(${mobileBg})` }}
        />

        {/* Content Container */}
        <div className="container mx-auto px-4 md:px-8 max-w-5xl">
          <div className="text-center">
            
            {/* Tagline / Subtitle */}
            <div className="flex items-center justify-center gap-2 mb-3">
              <span className="h-px w-6 bg-[#d9a78b]"></span>
              <span className="text-[11px] md:text-xs font-serif uppercase tracking-[0.25em] text-[#a07171]">The Wedding of</span>
              <span className="h-px w-6 bg-[#d9a78b]"></span>
            </div>

            {/* Couple Names */}
            <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl text-[#2d2626] font-normal tracking-tight mb-3">
              Sandeep <span className="font-script text-3xl sm:text-5xl md:text-6xl text-[#b36c73] font-light lowercase px-1">&</span> Prathyusha
            </h1>

            {/* Wedding Details */}
            <div className="flex flex-wrap items-center justify-center gap-y-2 gap-x-4 md:gap-x-6 text-[12px] md:text-sm text-[#736363] mb-6">
              <span className="flex items-center gap-1.5 font-serif">
                <Calendar className="w-3.5 h-3.5 text-[#b36c73]" />
                November 21, 2026
              </span>
              <span className="hidden sm:inline text-[#e6d8d0]">•</span>
              <span className="flex items-center gap-1.5 font-serif">
                <MapPin className="w-3.5 h-3.5 text-[#b36c73]" />
                Hyderabad, India
              </span>
            </div>

            {/* Rounded Box */}
            <div className="mx-auto max-w-2xl bg-white/70 backdrop-blur-md rounded-2xl md:rounded-3xl p-5 md:p-8 shadow-[0_4px_20px_rgba(0,0,0,0.03)] mb-6 md:mb-8 border border-white/50">
              <p className="text-[#554c4c] font-serif text-sm md:text-lg leading-relaxed mb-3 md:mb-4">
                A celebration of love, family and beautiful moments. <br className="hidden md:block"/>
                Join us in reliving the memories of our special day.
              </p>
              <div className="flex items-center justify-center gap-3">
                <div className="h-px w-8 bg-border"></div>
                <Heart className="w-2.5 h-2.5 text-[#b36c73] fill-[#b36c73]" />
                <div className="h-px w-8 bg-border"></div>
              </div>
            </div>
            
            {/* Live Count & Status Pill */}
            <div className="mt-6 flex justify-center">
               <div className="bg-[#fcf5f1] rounded-full px-5 py-2.5 flex items-center gap-3 md:gap-4 border border-[#f0e4dc] shadow-sm">
                  {isLive ? (
                    <div className="flex items-center gap-1.5 text-[#e03131] text-[11px] font-bold tracking-wider">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#e03131] opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-[#e03131]"></span>
                      </span>
                      LIVE
                    </div>
                  ) : connectionStatus === 'fallback' ? (
                    <button
                      type="button"
                      onClick={() => refresh()}
                      className="flex items-center gap-1.5 text-amber-700 hover:text-amber-800 text-[11px] font-semibold tracking-wider transition-colors cursor-pointer"
                      title="Real-time WebSocket disconnected. Gentle background sync active. Click to refresh now."
                    >
                      <RefreshCw className="w-3 h-3 text-amber-600" />
                      SYNC
                    </button>
                  ) : (
                    <div className="flex items-center gap-1.5 text-stone-500 text-[11px] font-medium tracking-wider">
                      <span className="inline-block h-2 w-2 rounded-full bg-stone-400 animate-pulse"></span>
                      SYNCING
                    </div>
                  )}
                  <div className="w-px h-4 bg-[#e6d8d0]"></div>
                  <p className="text-xs md:text-sm font-medium text-[#554c4c]">
                    <strong className="text-[#2d2626] font-semibold">{totalCount || photos.length}</strong> photos and counting...
                  </p>
               </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Container below Header */}
      <div className="container mx-auto px-4 md:px-8 max-w-7xl relative z-10 pt-0">
      
        {/* Search & Category Filter Bar */}
        <div className="flex flex-col items-center gap-3 mb-6 w-full max-w-4xl mx-auto">
          {/* Debounced Search Input */}
          <div className="relative w-full max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search wedding photos..."
              aria-label="Search wedding photos"
              className="w-full pl-9 pr-9 py-2 bg-white/80 backdrop-blur-sm border border-[#f0e4dc] rounded-full text-xs md:text-sm text-[#554c4c] placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-[#a67272]/30 focus:border-[#a67272] transition-all shadow-xs"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
                className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-stone-400 hover:text-stone-600 rounded-full cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Category Tabs */}
          <div className="flex overflow-x-auto pb-2 hide-scrollbar gap-2 px-2 max-w-full">
            {tabs.map((tab) => {
              let Icon = null;
              if (tab === "All") Icon = Grid;
              else if (tab === "Bride") Icon = Crown;
              else if (tab === "Groom") Icon = BowTieIcon;
              else if (tab === "Bride and Groom") Icon = Heart;
              
              const isSelected = activeTab === tab;
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-[11px] md:text-xs font-medium whitespace-nowrap transition-all duration-300 shadow-xs border cursor-pointer ${
                    isSelected 
                      ? "bg-[#a67272] text-white border-[#a67272] shadow-sm" 
                      : "bg-[#fcf5f1] text-[#554c4c] border-[#f0e4dc] hover:bg-[#f4ebe6]"
                  }`}
                >
                  {Icon && <Icon className="w-4 h-4" />}
                  {tab === "Bride and Groom" ? "Bride & Groom" : tab}
                </button>
              );
            })}
          </div>
        </div>
        
        {/* Gallery Grid or Skeleton / Error / Empty States */}
        {loading ? (
          <PhotoGridSkeleton count={20} />
        ) : error ? (
          <div className="text-center py-16 bg-white/70 backdrop-blur-md rounded-2xl border border-rose-100 max-w-md mx-auto p-6 shadow-sm my-8">
            <AlertCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-[#554c4c] mb-1">Failed to load gallery photos</p>
            <p className="text-xs text-muted-foreground mb-4">{error}</p>
            <button 
              type="button"
              onClick={() => fetchPhotos(true)} 
              className="px-5 py-2 bg-[#a67272] text-white rounded-full text-xs font-semibold hover:bg-[#8f5e5e] transition-colors flex items-center gap-2 mx-auto shadow-sm cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Try Again
            </button>
          </div>
        ) : photos.length === 0 ? (
          <div className="text-center py-20 bg-white/50 backdrop-blur-sm rounded-2xl border border-[#f0e4dc] max-w-md mx-auto p-8 my-8 shadow-sm">
            <Grid className="w-10 h-10 text-[#a07171]/40 mx-auto mb-3" />
            <p className="text-sm font-medium text-[#554c4c] mb-1">No photos found</p>
            <p className="text-xs text-muted-foreground">
              {debouncedSearch
                ? `No photos matched "${debouncedSearch}". Try a different search term.`
                : activeTab === "All" 
                  ? "No photos have been uploaded yet. Live photos from the photographer will appear here automatically." 
                  : `No photos found in category "${activeTab}" yet.`}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
            {photos.map((photo, index) => (
              <GalleryPhotoCard
                key={photo.id}
                photo={photo}
                index={index}
                onClick={openLightbox}
              />
            ))}
          </div>
        )}

        {/* Pagination Load More Button / Incremental loading */}
        {!loading && !error && nextPageUrl && (
          <div className="flex flex-col items-center justify-center my-8 gap-2">
            <button
              type="button"
              onClick={loadMorePhotos}
              disabled={loadingMore}
              className="px-6 py-2.5 rounded-full bg-white border border-[#f0e4dc] text-[#554c4c] hover:bg-[#fcf5f1] font-medium text-xs md:text-sm shadow-sm transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {loadingMore ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#a07171]" />
                  Loading next page...
                </>
              ) : (
                "Load More Photos"
              )}
            </button>
            {loadMoreError && (
              <p className="text-xs text-rose-500 font-medium flex items-center gap-1.5 mt-1">
                <AlertCircle className="w-3.5 h-3.5" />
                {loadMoreError}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Lazy-loaded Lightbox Modal */}
      {lightboxOpen && (
        <Suspense fallback={null}>
          <PhotoLightbox 
            photos={photos} 
            initialIndex={currentPhotoIndex} 
            onClose={closeLightbox} 
          />
        </Suspense>
      )}
    </div>
  );
}

// Simple BowTieIcon for Groom tab
function BowTieIcon({ className }: { className?: string }) {
  return (
    <svg 
      className={className} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 8l8 4-8 4V8z" />
      <path d="M20 8l-8 4 8 4V8z" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}
