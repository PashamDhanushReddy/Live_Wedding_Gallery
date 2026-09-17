import { useState } from "react";
import Lightbox from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import Thumbnails from "yet-another-react-lightbox/plugins/thumbnails";
import Counter from "yet-another-react-lightbox/plugins/counter";
import { Download, Trash2, ChevronLeft } from "lucide-react";

import "yet-another-react-lightbox/styles.css";
import "yet-another-react-lightbox/plugins/thumbnails.css";
import "yet-another-react-lightbox/plugins/counter.css";

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

  return (
    <>
      <Lightbox
        open={true}
        close={onClose}
        index={index}
        on={{ view: ({ index: currentIndex }) => setIndex(currentIndex) }}
        slides={photos.map((p) => ({ src: p.url, id: p.id }))}
        plugins={[Zoom, Thumbnails, Counter]}
        animation={{ fade: 250, swipe: 250 }}
        carousel={{ finite: false }}
        styles={{
          container: { backgroundColor: "rgba(0, 0, 0, 0.95)" },
          thumbnailsContainer: { backgroundColor: "rgba(0, 0, 0, 0.8)", padding: "12px", borderTop: "1px solid rgba(255,255,255,0.1)" },
          thumbnail: { borderRadius: "6px", overflow: "hidden" },
          root: { "--yarl__color_button": "rgba(255, 255, 255, 0.7)", "--yarl__color_button_active": "rgba(255, 255, 255, 1)" } as React.CSSProperties
        }}
        toolbar={{
          buttons: [
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
        thumbnails={{
          position: "bottom",
          width: 80,
          height: 80,
          border: 2,
          gap: 12,
          vignette: false,
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
      
      {/* Custom Back Button overlay mimicking the top-left one */}
      <div className="fixed top-0 left-0 p-4 z-[9999] pointer-events-none flex items-center">
        <button 
          onClick={onClose}
          className="flex items-center gap-1 text-white/70 hover:text-white pointer-events-auto p-2"
        >
          <ChevronLeft className="w-6 h-6" />
          <span className="hidden md:inline font-medium">Back to Gallery</span>
        </button>
      </div>
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
