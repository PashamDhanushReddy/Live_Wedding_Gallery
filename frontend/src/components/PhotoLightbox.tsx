import { useState, useEffect, useRef, useMemo } from "react";
import { createPortal } from "react-dom";
import Lightbox from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import { Download, Trash2, ChevronLeft } from "lucide-react";

import "yet-another-react-lightbox/styles.css";

export interface LightboxPhoto {
  id: number;
  url: string;
  thumbnail_url?: string;
  preview_url?: string;
  large_preview_url?: string;
  download_url?: string;
  secure_url?: string;
  category?: string;
}

interface PhotoLightboxProps {
  photos: LightboxPhoto[];
  initialIndex: number;
  onClose: () => void;
  onDelete?: (id: number) => void;
}

export default function PhotoLightbox({ photos, initialIndex, onClose, onDelete }: PhotoLightboxProps) {
  const [activePhotoId, setActivePhotoId] = useState(() => photos[initialIndex]?.id);
  const thumbBarRef = useRef<HTMLDivElement>(null);

  // Derive current index from the active photo ID
  let currentIndex = photos.findIndex(p => p.id === activePhotoId);
  if (currentIndex === -1) currentIndex = 0;

  // Prepare slides with large preview URLs for high-DPI display without downloading master RAWs
  const slides = useMemo(() => {
    return photos.map((p) => ({
      src: p.large_preview_url || p.preview_url || p.url,
      id: p.id,
    }));
  }, [photos]);

  const handleDownload = async () => {
    const currentPhoto = photos[currentIndex];
    // Master high-resolution asset URL directly from CDN with attachment header
    const dlUrl = currentPhoto?.download_url || currentPhoto?.secure_url || currentPhoto?.url;
    if (!dlUrl) return;

    try {
      const response = await fetch(dlUrl);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      const filename = currentPhoto.url.split('/').pop()?.split('?')[0] || `wedding-photo-${currentPhoto.id}.jpg`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (e) {
      console.error("Download failed, opening direct URL", e);
      window.open(dlUrl, '_blank');
    }
  };

  const handleDelete = () => {
    const currentPhoto = photos[currentIndex];
    if (!currentPhoto) return;
    if (onDelete) onDelete(currentPhoto.id);
  };

  // Scroll active thumbnail into center view
  useEffect(() => {
    const el = document.getElementById(`thumb-${currentIndex}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [currentIndex]);

  // Prevent thumbnail scrolling from triggering main image swipe gestures
  useEffect(() => {
    const el = thumbBarRef.current;
    if (!el) return;
    const stopProp = (e: Event) => e.stopPropagation();
    
    el.addEventListener('touchstart', stopProp, { passive: true });
    el.addEventListener('touchmove', stopProp, { passive: true });
    el.addEventListener('touchend', stopProp, { passive: true });
    el.addEventListener('pointerdown', stopProp);
    el.addEventListener('pointermove', stopProp);
    el.addEventListener('wheel', stopProp);

    return () => {
      el.removeEventListener('touchstart', stopProp);
      el.removeEventListener('touchmove', stopProp);
      el.removeEventListener('touchend', stopProp);
      el.removeEventListener('pointerdown', stopProp);
      el.removeEventListener('pointermove', stopProp);
      el.removeEventListener('wheel', stopProp);
    };
  }, []);

  // Windowed thumbnail strip: only render +/- 12 items around the active thumbnail
  const WINDOW_RADIUS = 12;
  const startIndex = Math.max(0, currentIndex - WINDOW_RADIUS);
  const endIndex = Math.min(photos.length - 1, currentIndex + WINDOW_RADIUS);
  const visibleThumbs = photos.slice(startIndex, endIndex + 1);

  // Approximate slot width (thumb 64px/80px + 8px gap)
  const leftSpacerWidth = startIndex * 76;
  const rightSpacerWidth = (photos.length - 1 - endIndex) * 76;

  return (
    <>
      <Lightbox
        open={true}
        close={onClose}
        index={currentIndex}
        on={{ view: ({ index: newIndex }) => setActivePhotoId(photos[newIndex]?.id) }}
        slides={slides}
        plugins={[Zoom]}
        animation={{ fade: 250, swipe: 250 }}
        carousel={{ finite: false }}
        styles={{
          container: { backgroundColor: "rgba(0, 0, 0, 0.95)" },
          root: { "--yarl__color_button": "rgba(255, 255, 255, 0.7)", "--yarl__color_button_active": "rgba(255, 255, 255, 1)" } as any
        }}
        toolbar={{
          buttons: [
            <div key="left-group" className="fixed top-0 left-0 p-2 md:p-4 flex items-center z-[100000]">
              <button 
                type="button" 
                className="flex items-center gap-1 text-white hover:text-white p-2 bg-black/40 hover:bg-black/60 rounded-lg transition-colors cursor-pointer" 
                onClick={onClose} 
                title="Back to gallery (Esc)"
                aria-label="Back to gallery"
              >
                <ChevronLeft className="w-6 h-6 md:w-8 md:h-8" />
                <span className="hidden md:inline font-medium text-base md:text-lg pr-1">Back to Gallery</span>
              </button>
              <div className="text-white/90 text-sm font-medium bg-black/40 px-3 py-1.5 rounded-full flex items-center justify-center ml-2 md:ml-4">
                {currentIndex + 1} / {photos.length}
              </div>
            </div>,
            <button key="download" type="button" className="yarl__button cursor-pointer" onClick={handleDownload} title="Download Original Quality" aria-label="Download original photo">
              <Download className="w-5 h-5 md:w-6 md:h-6" />
            </button>,
            onDelete ? (
              <button key="delete" type="button" className="yarl__button cursor-pointer" onClick={handleDelete} title="Delete Photo" aria-label="Delete photo">
                <Trash2 className="w-5 h-5 md:w-6 md:h-6 text-rose-500/80 hover:text-rose-500" />
              </button>
            ) : null,
            "close",
          ].filter(Boolean) as React.ReactNode[],
        }}
        render={{
          iconClose: () => <XIcon />,
          iconPrev: () => <ChevronLeft className="w-8 h-8" />,
          iconNext: () => <ChevronLeft className="w-8 h-8 rotate-180" />,
        }}
        zoom={{
          maxZoomPixelRatio: 5,
          zoomInMultiplier: 2,
          doubleTapDelay: 300,
          doubleClickDelay: 300,
          keyboardMoveDistance: 50,
          wheelZoomDistanceFactor: 100,
          pinchZoomDistanceFactor: 100,
          scrollToZoom: false,
        }}
      />
      
      {createPortal(
        <>
          {/* Custom Windowed Thumbnails Bar */}
          <div 
            ref={thumbBarRef}
            className="fixed bottom-0 left-0 right-0 h-24 bg-black/80 p-2 flex gap-2 overflow-x-auto hide-scrollbar items-center border-t border-white/10 scroll-smooth z-[99999] pointer-events-auto"
            role="region"
            aria-label="Photo thumbnails"
          >
            {/* Left Spacer to preserve scroll offset */}
            {leftSpacerWidth > 0 && (
              <div style={{ flexShrink: 0, width: `${leftSpacerWidth}px` }} aria-hidden="true" />
            )}

            {visibleThumbs.map((p, offset) => {
              const realIdx = startIndex + offset;
              const isSelected = realIdx === currentIndex;
              return (
                <button 
                  key={p.id}
                  id={`thumb-${realIdx}`}
                  onClick={() => setActivePhotoId(p.id)}
                  aria-label={`View photo ${realIdx + 1}`}
                  className={`flex-shrink-0 h-16 w-16 md:h-20 md:w-20 rounded-md overflow-hidden border-2 transition-all duration-300 cursor-pointer ${
                    isSelected ? 'border-[#a07171] opacity-100 scale-105' : 'border-transparent opacity-40 hover:opacity-80 scale-100'
                  }`}
                >
                  <img 
                    src={p.thumbnail_url || p.preview_url || p.url} 
                    alt={`Thumbnail ${realIdx + 1}`}
                    loading="lazy" 
                    decoding="async" 
                    className="w-full h-full object-cover" 
                  />
                </button>
              );
            })}

            {/* Right Spacer to preserve scroll offset */}
            {rightSpacerWidth > 0 && (
              <div style={{ flexShrink: 0, width: `${rightSpacerWidth}px` }} aria-hidden="true" />
            )}
          </div>
        </>,
        document.body
      )}
    </>
  );
}

// Accessible X icon for the default close button
function XIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
  );
}
