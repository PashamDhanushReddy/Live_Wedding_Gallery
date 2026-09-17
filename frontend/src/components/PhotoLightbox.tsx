  import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import Lightbox from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import { Download, Trash2, ChevronLeft } from "lucide-react";

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

  // Scroll active thumbnail into center view
  useEffect(() => {
    const el = document.getElementById(`thumb-${index}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [index]);

  return (
    <>
      <Lightbox
        open={true}
        close={onClose}
        index={index}
        on={{ view: ({ index: currentIndex }) => setIndex(currentIndex) }}
        slides={photos.map((p) => ({ src: p.url, id: p.id }))}
        plugins={[Zoom]}
        animation={{ fade: 250, swipe: 250 }}
        carousel={{ finite: false }}
        styles={{
          container: { backgroundColor: "rgba(0, 0, 0, 0.95)" },
          root: { "--yarl__color_button": "rgba(255, 255, 255, 0.7)", "--yarl__color_button_active": "rgba(255, 255, 255, 1)" } as React.CSSProperties
        }}
        toolbar={{
          buttons: [
            <div key="left-group" className="fixed top-0 left-0 p-2 md:p-4 flex items-center z-[100000]">
              <button 
                type="button" 
                className="flex items-center gap-1 text-white hover:text-white p-2 bg-black/40 hover:bg-black/60 rounded-lg transition-colors" 
                onClick={onClose} 
                title="Back"
              >
                <ChevronLeft className="w-6 h-6 md:w-8 md:h-8" />
                <span className="hidden md:inline font-medium text-base md:text-lg pr-1">Back to Gallery</span>
              </button>
              <div className="text-white/90 text-sm font-medium bg-black/40 px-3 py-1.5 rounded-full flex items-center justify-center ml-2 md:ml-4">
                {index + 1} / {photos.length}
              </div>
            </div>,
            <button key="download" type="button" className="yarl__button" onClick={handleDownload} title="Download">
              <Download className="w-5 h-5 md:w-6 md:h-6" />
            </button>,
            onDelete ? (
              <button key="delete" type="button" className="yarl__button" onClick={handleDelete} title="Delete">
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
          {/* Custom Native-Scrollable Thumbnails Bar */}
          <div className="fixed bottom-0 left-0 right-0 h-24 bg-black/80 p-2 flex gap-2 overflow-x-auto hide-scrollbar items-center border-t border-white/10 scroll-smooth z-[99999] pointer-events-auto">
            {photos.map((p, idx) => (
              <button 
                key={p.id}
                id={`thumb-${idx}`}
                onClick={() => setIndex(idx)}
                className={`flex-shrink-0 h-16 w-16 md:h-20 md:w-20 rounded-md overflow-hidden border-2 transition-all duration-300 ${idx === index ? 'border-[#a07171] opacity-100 scale-105' : 'border-transparent opacity-40 hover:opacity-80 scale-100'}`}
              >
                <img src={p.url} loading="lazy" decoding="async" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        </>,
        document.body
      )}
    </>
  );
}

// Simple X icon for the default close button
function XIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
  );
}
