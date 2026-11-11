import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from "react";
import { Calendar, MapPin, Heart, Grid, Crown, Search, X, ShieldCheck, RefreshCw, Sparkles } from "lucide-react";
import { WEDDING_SLUG, GALLERY_TABS } from "../config";
import { useWeddingRealtime } from "../hooks/useWeddingRealtime";
import { useDebounce } from "../hooks/useDebounce";
import GalleryPhotoCard, { type GalleryPhotoItem } from "../components/ui/GalleryPhotoCard";
import FaceScanner from "../components/ui/FaceScanner";

// Dynamic import of PhotoLightbox so yet-another-react-lightbox isn't in initial bundle
const PhotoLightbox = lazy(() => import("../components/PhotoLightbox"));

import bgImage from "../assets/bg_blue.png";
import mobileBg from "../assets/mobile_bg.png";
import weddingLogo from "../assets/wedding-logo.png";

export default function GalleryPage() {
  const [activeTab, setActiveTab] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 350);

  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);

  // Private Guest Session State
  const [isFaceScanned, setIsFaceScanned] = useState(false);
  const [selfieThumb, setSelfieThumb] = useState<string | null>(null);
  const [allMatchedPhotos, setAllMatchedPhotos] = useState<GalleryPhotoItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);

  // Check existing face session on mount
  useEffect(() => {
    try {
      const cachedPhotosJson = sessionStorage.getItem("guest_matched_photos");
      const cachedThumb = sessionStorage.getItem("guest_selfie_thumb");
      if (cachedPhotosJson) {
        const parsed: GalleryPhotoItem[] = JSON.parse(cachedPhotosJson);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setAllMatchedPhotos(parsed);
          setTotalCount(parsed.length);
          setSelfieThumb(cachedThumb);
          setIsFaceScanned(true);
        }
      }
    } catch (e) {
      console.warn("Could not parse cached guest photos", e);
    }
  }, []);

  const handlePhotosFound = (photos: GalleryPhotoItem[], selfieUrl: string, count: number) => {
    try {
      sessionStorage.setItem("guest_matched_photos", JSON.stringify(photos));
      sessionStorage.setItem("guest_selfie_thumb", selfieUrl);
    } catch (_) {}
    setAllMatchedPhotos(photos);
    setTotalCount(count);
    setSelfieThumb(selfieUrl);
    setIsFaceScanned(true);
  };

  const handleRescan = () => {
    try {
      sessionStorage.removeItem("guest_matched_photos");
      sessionStorage.removeItem("guest_selfie_thumb");
    } catch (_) {}
    setAllMatchedPhotos([]);
    setSelfieThumb(null);
    setIsFaceScanned(false);
  };

  const tabs = GALLERY_TABS;

  // Filter among the guest's face-matched photos
  const filteredPhotos = useMemo(() => {
    let result = allMatchedPhotos;

    if (activeTab !== "All") {
      const target = activeTab.toLowerCase().replace(/_/g, ' ');
      result = result.filter(p => {
        const cat = (p.category || "").toLowerCase().replace(/_/g, ' ');
        return cat === target;
      });
    }

    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase().trim();
      result = result.filter(p =>
        (p.category || "").toLowerCase().includes(q) ||
        String(p.id).includes(q)
      );
    }

    return result;
  }, [allMatchedPhotos, activeTab, debouncedSearch]);

  // Real-time synchronization via WebSocket for live event additions
  const handleDeletePhoto = useCallback((photoId: number) => {
    setAllMatchedPhotos(prev => {
      const updated = prev.filter(p => p.id !== photoId);
      try {
        sessionStorage.setItem("guest_matched_photos", JSON.stringify(updated));
      } catch (_) {}
      return updated;
    });
  }, []);

  const { isLive } = useWeddingRealtime<GalleryPhotoItem>({
    slug: WEDDING_SLUG,
    activeTab,
    mapPhoto: (p) => p,
    onNewPhotos: () => {
      // In live mode, photographer shots are ingested continuously
    },
    onDeletePhoto: handleDeletePhoto,
    onTotalCountChange: () => {},
    enableApiSync: false,
  });

  const openLightbox = useCallback((index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxOpen(false);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#fffaf7] to-[#fcfaf8] pb-16">
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

            {/* Wedding Emblem Logo */}
            <div className="flex justify-center mb-4">
              <div className="relative group">
                <img
                  src={weddingLogo}
                  alt="Sandeep & Prathyusha Wedding"
                  className="w-28 h-28 sm:w-36 sm:h-36 md:w-44 md:h-44 object-contain drop-shadow-md hover:scale-105 transition-transform duration-300"
                />
              </div>
            </div>

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
            <div className="flex flex-wrap items-center justify-center gap-y-2 gap-x-4 md:gap-x-6 text-[12px] md:text-sm text-[#736363] mb-4">
              <span className="flex items-center gap-1.5 font-serif">
                <Calendar className="w-3.5 h-3.5 text-[#b36c73]" />
                November 21, 2026
              </span>
              <span className="hidden sm:inline text-[#e6d8d0]">•</span>
              <span className="flex items-center gap-1.5 font-serif">
                <MapPin className="w-3.5 h-3.5 text-[#b36c73]" />
                Nizamabad, Telangana.
              </span>
            </div>

            {/* Privacy Guarantee Badge */}
            <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-sm border border-[#a07171]/20 px-4 py-1.5 rounded-full text-xs text-[#554c4c] shadow-xs mb-4">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Private Live Gallery — Photos are personalized via AI face recognition</span>
            </div>

          </div>
        </div>
      </div>

      {/* Main Body */}
      <div className="container mx-auto px-4 md:px-8 max-w-7xl relative z-10 pt-2">

        {!isFaceScanned ? (
          /* Face Scanner Prompt: Scans user face in background upon loading */
          <div className="my-4">
            <FaceScanner onPhotosFound={handlePhotosFound} />
          </div>
        ) : (
          /* Personalized Unlocked Gallery */
          <div>
            {/* Guest Face Verified Banner */}
            <div className="max-w-4xl mx-auto bg-white/80 backdrop-blur-md rounded-2xl md:rounded-3xl p-4 sm:p-5 border border-[#f0e4dc] shadow-sm mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                {selfieThumb ? (
                  <img
                    src={selfieThumb}
                    alt="Your Face"
                    className="w-12 h-12 rounded-full object-cover border-2 border-[#b36c73] shadow-sm shrink-0"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-[#fcf5f1] border-2 border-[#b36c73] flex items-center justify-center text-[#b36c73] shrink-0">
                    <Sparkles className="w-6 h-6" />
                  </div>
                )}
                <div className="text-left">
                  <div className="flex items-center gap-2">
                    <h3 className="font-serif text-base sm:text-lg font-medium text-[#2d2626]">
                      Your Personal Wedding Photos
                    </h3>
                    {isLive && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                        LIVE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#736363]">
                    Showing <strong className="text-[#2d2626]">{filteredPhotos.length}</strong> of {totalCount || allMatchedPhotos.length} photos featuring you
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleRescan}
                  className="flex-1 sm:flex-initial px-4 py-2 bg-white border border-[#f0e4dc] text-[#554c4c] hover:bg-[#fcf5f1] text-xs font-medium rounded-full shadow-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  title="Scan with a different face or retake selfie"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-[#a07171]" />
                  Rescan Face
                </button>
              </div>
            </div>

            {/* Search & Category Filter Bar */}
            <div className="flex flex-col items-center gap-3 mb-6 w-full max-w-4xl mx-auto">
              {/* Debounced Search Input */}
              <div className="relative w-full max-w-md">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter your photos by event..."
                  aria-label="Filter your photos"
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

            {/* Photo Grid or Empty State */}
            {filteredPhotos.length === 0 ? (
              <div className="text-center py-20 bg-white/50 backdrop-blur-sm rounded-2xl border border-[#f0e4dc] max-w-md mx-auto p-8 my-8 shadow-sm">
                <Grid className="w-10 h-10 text-[#a07171]/40 mx-auto mb-3" />
                <p className="text-sm font-medium text-[#554c4c] mb-1">No matching photos found</p>
                <p className="text-xs text-muted-foreground mb-4">
                  {debouncedSearch
                    ? `No photos matched "${debouncedSearch}". Try clearing your search.`
                    : activeTab !== "All"
                    ? `You don't have any photos under "${activeTab}" yet.`
                    : "No wedding photos were found matching your face. The photographer is actively shooting, or you can try rescanning your face."}
                </p>
                <button
                  type="button"
                  onClick={handleRescan}
                  className="px-5 py-2 bg-[#a67272] text-white rounded-full text-xs font-semibold hover:bg-[#8f5e5e] transition-colors inline-flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Rescan Face
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
                {filteredPhotos.map((photo, index) => (
                  <GalleryPhotoCard
                    key={photo.id}
                    photo={photo}
                    index={index}
                    onClick={openLightbox}
                  />
                ))}
              </div>
            )}
          </div>
        )}

      </div>

      {/* Lazy-loaded Lightbox Modal */}
      {lightboxOpen && (
        <Suspense fallback={null}>
          <PhotoLightbox
            photos={filteredPhotos}
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
