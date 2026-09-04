'use client';

import { useState } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomIn, Download, Share2, ChevronLeft, ChevronRight } from 'lucide-react';
import { useLiveGallery } from '@/hooks/useLiveGallery';

export type Photo = {
  id: number;
  url: string;
  display_url: string;
  width?: number;
  height?: number;
};

export default function Gallery({ initialPhotos, weddingSlug, sessionId }: { initialPhotos: Photo[], weddingSlug: string, sessionId?: string | null }) {
  const photos = useLiveGallery(weddingSlug, initialPhotos, sessionId);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const selectedIndex = selectedPhoto ? photos.findIndex(p => p.id === selectedPhoto.id) : -1;

  const goToNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedIndex < photos.length - 1) {
      setSelectedPhoto(photos[selectedIndex + 1]);
    }
  };

  const goToPrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedIndex > 0) {
      setSelectedPhoto(photos[selectedIndex - 1]);
    }
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedPhoto) return;
    try {
      const response = await fetch(selectedPhoto.display_url || selectedPhoto.url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `wedding-photo-${selectedPhoto.id}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading image:", err);
    }
  };

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedPhoto) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Wedding Photo',
          text: 'Check out this photo from the wedding!',
          url: selectedPhoto.display_url || selectedPhoto.url,
        });
      } catch (err) {
        console.error("Error sharing:", err);
      }
    }
  };

  // In Phase 6, we'll add WebSocket listener here to update 'photos'

  return (
    <>
      <div className="columns-1 sm:columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4 p-4">
        <AnimatePresence>
          {photos.length === 0 && (
             <div className="col-span-full text-center text-neutral-500 py-20">
               No photos uploaded yet.
             </div>
          )}
          {photos.map((photo) => (
            <motion.div
              key={photo.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="relative group cursor-pointer break-inside-avoid overflow-hidden rounded-xl bg-neutral-900 border border-white/5"
              onClick={() => setSelectedPhoto(photo)}
            >
              <Image 
                src={photo.url} 
                alt={`Photo ${photo.id}`}
                width={photo.width || 800}
                height={photo.height || 800}
                className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-105"
                unoptimized
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                <ZoomIn className="w-8 h-8 text-white drop-shadow-lg" />
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {selectedPhoto && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/95 flex flex-col items-center justify-center p-4 sm:p-8"
            onClick={() => setSelectedPhoto(null)}
          >
            {/* Top Bar Controls */}
            <div className="absolute top-0 left-0 right-0 p-6 flex justify-between items-center z-10 pointer-events-none">
              <div className="text-white/80 text-sm tracking-widest font-medium pointer-events-auto bg-black/40 px-3 py-1 rounded-full backdrop-blur-md">
                {selectedIndex + 1} / {photos.length}
              </div>
              <button 
                className="text-white/70 hover:text-white bg-black/40 p-2 rounded-full backdrop-blur-md pointer-events-auto transition-colors"
                onClick={() => setSelectedPhoto(null)}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {selectedIndex > 0 && (
              <button 
                className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2"
                onClick={goToPrev}
              >
                <ChevronLeft className="w-8 h-8" />
              </button>
            )}

            {selectedIndex < photos.length - 1 && (
              <button 
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2"
                onClick={goToNext}
              >
                <ChevronRight className="w-8 h-8" />
              </button>
            )}

            <motion.div 
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="relative w-full max-w-6xl max-h-full flex items-center justify-center flex-1 py-12"
              onClick={(e) => e.stopPropagation()}
            >
              <Image 
                src={selectedPhoto.display_url || selectedPhoto.url} 
                alt={`Full Photo ${selectedPhoto.id}`}
                width={selectedPhoto.width || 1920}
                height={selectedPhoto.height || 1080}
                className="max-w-full max-h-[80vh] w-auto h-auto object-contain shadow-2xl"
                unoptimized
              />
            </motion.div>

            <div className="absolute bottom-6 left-0 right-0 flex justify-center items-center gap-6 z-10">
              <button onClick={handleDownload} className="flex items-center gap-2 text-white/80 hover:text-white bg-white/10 px-6 py-2.5 rounded-full backdrop-blur-md transition-colors text-sm font-medium">
                <Download className="w-4 h-4" />
                Download
              </button>
              <button onClick={handleShare} className="flex items-center gap-2 text-white/80 hover:text-white bg-white/10 px-6 py-2.5 rounded-full backdrop-blur-md transition-colors text-sm font-medium">
                <Share2 className="w-4 h-4" />
                Share
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
