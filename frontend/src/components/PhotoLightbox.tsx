import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Heart, Download, Share2, Info } from "lucide-react";
import { useState } from "react";

interface Photo {
  id: number;
  url: string;
}

interface PhotoLightboxProps {
  photos: Photo[];
  initialIndex: number;
  onClose: () => void;
}

export default function PhotoLightbox({ photos, initialIndex, onClose }: PhotoLightboxProps) {
  // Track by ID so that if new photos are prepended, we don't accidentally switch images
  const [currentPhotoId, setCurrentPhotoId] = useState(photos[initialIndex]?.id);

  // Find the actual index of the current photo
  const currentIndex = photos.findIndex((p) => p.id === currentPhotoId);
  const displayIndex = currentIndex >= 0 ? currentIndex : 0;
  const currentPhoto = photos[displayIndex];

  const handleNext = () => {
    const nextIndex = (displayIndex + 1) % photos.length;
    setCurrentPhotoId(photos[nextIndex].id);
  };

  const handlePrev = () => {
    const prevIndex = (displayIndex - 1 + photos.length) % photos.length;
    setCurrentPhotoId(photos[prevIndex].id);
  };

  const handleDownload = async () => {
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

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] bg-black/95 flex flex-col md:flex-row"
      >
        {/* Top Header (Mobile mainly, but visible on desktop too) */}
        <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-center z-10">
          <button 
            onClick={onClose}
            className="flex items-center gap-2 text-white/70 hover:text-white"
          >
            <ChevronLeft className="w-5 h-5" />
            <span className="hidden md:inline">Back to Gallery</span>
          </button>
          
          <div className="text-white/70 text-sm font-medium">
            {displayIndex + 1} / {photos.length}
          </div>
          
          <button onClick={onClose} className="p-2 text-white/70 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Main Image Area */}
        <div className="flex-1 relative flex items-center justify-center p-4 md:p-12 mb-24 md:mb-0">
          <button 
            onClick={handlePrev}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-10"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          
          <motion.img
            key={currentPhotoId}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
            src={currentPhoto?.url}
            alt="Wedding Photo"
            className="max-w-full max-h-[60vh] md:max-h-[85vh] object-contain rounded-md touch-none"
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.7}
            onDragEnd={(e, { offset, velocity }) => {
              const swipe = Math.abs(offset.x) * velocity.x;
              if (swipe < -10000) {
                handleNext();
              } else if (swipe > 10000) {
                handlePrev();
              }
            }}
          />
          
          <button 
            onClick={handleNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-10"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>

        {/* Sidebar / Bottom Actions */}
        <div className="w-full md:w-24 bg-black/80 flex md:flex-col items-center justify-center gap-6 p-4 md:py-12 border-t md:border-t-0 md:border-l border-white/10 absolute bottom-24 md:relative md:bottom-auto z-20">
          <button className="flex flex-col items-center gap-2 text-white/70 hover:text-primary transition-colors">
            <Heart className="w-6 h-6" />
            <span className="text-xs">Like</span>
          </button>
          <button onClick={handleDownload} className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors">
            <Download className="w-6 h-6" />
            <span className="text-xs">Download</span>
          </button>
          <button className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors">
            <Share2 className="w-6 h-6" />
            <span className="text-xs">Share</span>
          </button>
          <button className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors">
            <Info className="w-6 h-6" />
            <span className="text-xs">Details</span>
          </button>
        </div>
        
        {/* Carousel Strip (Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 md:right-24 h-24 bg-black/80 p-2 flex gap-2 overflow-x-auto hide-scrollbar items-center border-t border-white/10">
          {photos.map((p) => (
            <button 
              key={p.id}
              onClick={() => setCurrentPhotoId(p.id)}
              className={`flex-shrink-0 h-16 w-16 md:h-20 md:w-20 rounded-md overflow-hidden border-2 transition-all ${p.id === currentPhotoId ? 'border-primary' : 'border-transparent opacity-50 hover:opacity-100'}`}
            >
              <img src={p.url} className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
