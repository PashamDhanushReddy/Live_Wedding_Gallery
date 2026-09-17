import { useState, useRef, useEffect } from "react";
import Lightbox from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import type { ControllerRef } from "yet-another-react-lightbox";
import { X, ChevronLeft, ChevronRight, Download, Trash2 } from "lucide-react";

import "yet-another-react-lightbox/styles.css";

interface Photo {
  id: number;
  url: string;
}

interface PhotoLightboxProps {
  photos: Photo[];
  initialIndex: number;
  onClose: () => void;
  onDelete?: (id: number) => void;
}

export default function PhotoLightbox({ photos, initialIndex, onClose, onDelete }: PhotoLightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const lightboxRef = useRef<ControllerRef>(null);

  const handleDownload = async () => {
    const currentPhoto = photos[index];
    if (!currentPhoto?.url) return;
    try {
      const response = await fetch(currentPhoto.url);
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
      console.error("Download failed", e);
      window.open(currentPhoto.url, '_blank');
    }
  };

  const handleDelete = () => {
    const currentPhoto = photos[index];
    if (!currentPhoto) return;
    if (onDelete) onDelete(currentPhoto.id);
  };

  // Scroll thumbnail into view automatically
  useEffect(() => {
    const el = document.getElementById(`thumb-${index}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [index]);

  return (
    <>
      {/* The ultra-smooth YARL Slider handling purely the background physics and images */}
      <Lightbox
        open={true}
        close={onClose}
        index={index}
        on={{ view: ({ index: currentIndex }) => setIndex(currentIndex) }}
        slides={photos.map((p) => ({ src: p.url, id: p.id }))}
        plugins={[Zoom]}
        controller={{ ref: lightboxRef }}
        animation={{ fade: 250, swipe: 250 }}
        carousel={{ finite: false }}
        render={{
          buttonPrev: () => null,
          buttonNext: () => null,
          buttonClose: () => null,
          toolbar: () => null, // Hide default toolbar entirely
        }}
        styles={{
          root: { "--yarl__color_backdrop": "rgba(0, 0, 0, 0.95)" } as React.CSSProperties
        }}
        zoom={{
          maxZoomPixelRatio: 5,
          zoomInMultiplier: 2,
          doubleTapDelay: 300,
          doubleClickDelay: 300,
          scrollToZoom: false,
        }}
      />

      {/* The exact previous Custom UI as an overlay */}
      <div className="fixed inset-0 z-[10000] flex flex-col md:flex-row pointer-events-none">
        
        {/* Top Header */}
        <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center z-20 pointer-events-none">
          <button 
            onClick={onClose}
            className="flex items-center gap-2 text-white/70 hover:text-white pointer-events-auto"
          >
            <ChevronLeft className="w-5 h-5" />
            <span className="hidden md:inline">Back to Gallery</span>
          </button>
          
          <div className="text-white/70 text-sm font-medium">
            {index + 1} / {photos.length}
          </div>
          
          <button onClick={onClose} className="p-2 text-white/70 hover:text-white pointer-events-auto">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Main Image Area with Custom Navigation Arrows */}
        <div className="flex-1 relative flex items-center justify-center mb-24 md:mb-0 w-full h-full overflow-hidden pointer-events-none">
          <button 
            onClick={() => lightboxRef.current?.prev()}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-20 pointer-events-auto"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          
          <button 
            onClick={() => lightboxRef.current?.next()}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-20 pointer-events-auto"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>

        {/* Sidebar / Bottom Actions */}
        <div className="w-full md:w-24 bg-black/80 flex md:flex-col items-center justify-center gap-6 p-4 md:py-12 border-t md:border-t-0 md:border-l border-white/10 absolute bottom-24 md:relative md:bottom-auto z-20 pointer-events-auto">
          <button onClick={handleDownload} className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors">
            <Download className="w-6 h-6" />
            <span className="text-xs">Download</span>
          </button>
          
          {onDelete && (
            <button 
              onClick={handleDelete} 
              className="flex flex-col items-center gap-2 text-rose-500/70 hover:text-rose-500 transition-colors"
            >
              <Trash2 className="w-6 h-6" />
              <span className="text-xs">Delete</span>
            </button>
          )}
        </div>
        
        {/* Carousel Strip (Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 md:right-24 h-24 bg-black/80 p-2 flex gap-2 overflow-x-auto hide-scrollbar items-center border-t border-white/10 scroll-smooth pointer-events-auto">
          {photos.map((p, idx) => (
            <button 
              key={p.id}
              id={`thumb-${idx}`}
              onClick={() => setIndex(idx)}
              className={`flex-shrink-0 h-16 w-16 md:h-20 md:w-20 rounded-md overflow-hidden border-2 transition-all ${idx === index ? 'border-primary' : 'border-transparent opacity-50 hover:opacity-100'}`}
            >
              <img src={p.url} loading="lazy" className="w-full h-full object-cover pointer-events-none" />
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
