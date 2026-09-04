'use client';

import { useState } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomIn } from 'lucide-react';
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
            className="fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-4 sm:p-8"
            onClick={() => setSelectedPhoto(null)}
          >
            <button 
              className="absolute top-6 right-6 text-white/70 hover:text-white bg-black/50 p-2 rounded-full backdrop-blur-md"
              onClick={() => setSelectedPhoto(null)}
            >
              <X className="w-6 h-6" />
            </button>
            <motion.div 
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              className="relative w-full max-w-6xl max-h-full flex items-center justify-center"
              onClick={(e) => e.stopPropagation()}
            >
              <Image 
                src={selectedPhoto.display_url || selectedPhoto.url} 
                alt={`Full Photo ${selectedPhoto.id}`}
                width={selectedPhoto.width || 1920}
                height={selectedPhoto.height || 1080}
                className="max-w-full max-h-[85vh] w-auto h-auto object-contain rounded-md shadow-2xl"
                unoptimized
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
