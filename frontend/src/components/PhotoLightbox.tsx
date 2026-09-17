import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Download, Trash2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { Swiper, SwiperSlide } from 'swiper/react';
import { Zoom } from 'swiper/modules';
import type { Swiper as SwiperType } from 'swiper';

import 'swiper/css';
import 'swiper/css/zoom';

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
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const swiperRef = useRef<SwiperType | null>(null);

  const currentPhoto = photos[activeIndex];

  const handleNext = () => {
    swiperRef.current?.slideNext();
  };

  const handlePrev = () => {
    swiperRef.current?.slidePrev();
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
            {activeIndex + 1} / {photos.length}
          </div>
          
          <button onClick={onClose} className="p-2 text-white/70 hover:text-white pointer-events-auto">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Main Image Area with Swiper */}
        <div className="flex-1 relative flex items-center justify-center mb-24 md:mb-0 w-full h-full overflow-hidden">
          
          {/* Custom Navigation Arrows */}
          <button 
            onClick={handlePrev}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-20"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>

          <Swiper
            modules={[Zoom]}
            zoom={true}
            spaceBetween={20}
            slidesPerView={1}
            initialSlide={initialIndex}
            onSwiper={(swiper) => (swiperRef.current = swiper)}
            onSlideChange={(swiper) => setActiveIndex(swiper.activeIndex)}
            className="w-full h-full"
          >
            {photos.map((photo) => (
              <SwiperSlide key={photo.id}>
                <div className="swiper-zoom-container w-full h-full p-4 md:p-12 pb-24 md:pb-12">
                  <img 
                    src={photo.url} 
                    alt="Wedding Photo" 
                    className="max-w-full max-h-[70vh] md:max-h-[85vh] object-contain rounded-md"
                  />
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
          
          <button 
            onClick={handleNext}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 text-white rounded-full hover:bg-black/80 z-20"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>

        {/* Sidebar / Bottom Actions */}
        <div className="w-full md:w-24 bg-black/80 flex md:flex-col items-center justify-center gap-6 p-4 md:py-12 border-t md:border-t-0 md:border-l border-white/10 absolute bottom-24 md:relative md:bottom-auto z-20">
          <button onClick={handleDownload} className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors">
            <Download className="w-6 h-6" />
            <span className="text-xs">Download</span>
          </button>
          
          {onDelete && (
            <button 
              onClick={() => {
                if (currentPhoto) onDelete(currentPhoto.id);
              }} 
              className="flex flex-col items-center gap-2 text-rose-500/70 hover:text-rose-500 transition-colors"
            >
              <Trash2 className="w-6 h-6" />
              <span className="text-xs">Delete</span>
            </button>
          )}
        </div>
        
        {/* Carousel Strip (Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 md:right-24 h-24 bg-black/80 p-2 flex gap-2 overflow-x-auto hide-scrollbar items-center border-t border-white/10">
          {photos.map((p, idx) => (
            <button 
              key={p.id}
              onClick={() => swiperRef.current?.slideTo(idx)}
              className={`flex-shrink-0 h-16 w-16 md:h-20 md:w-20 rounded-md overflow-hidden border-2 transition-all ${idx === activeIndex ? 'border-primary' : 'border-transparent opacity-50 hover:opacity-100'}`}
            >
              <img src={p.url} className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
