'use client';

import { useState, useEffect, use } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { useLiveGallery } from '@/hooks/useLiveGallery';

export default function TvDisplayPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const photos = useLiveGallery(slug, []);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Slideshow logic
  useEffect(() => {
    if (photos.length <= 1) return;
    
    // Switch photo every 8 seconds
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % photos.length);
    }, 8000);
    
    return () => clearInterval(interval);
  }, [photos.length]);

  // When a new photo arrives (photos array changes), show the newest one immediately
  useEffect(() => {
    if (photos.length > 0) {
      setCurrentIndex(0); // Assuming new photos are added to the front
    }
  }, [photos]);

  if (photos.length === 0) {
    return (
      <div className="bg-black min-h-screen flex items-center justify-center">
        <h1 className="text-white/50 text-2xl font-light tracking-widest uppercase animate-pulse">Waiting for photos...</h1>
      </div>
    );
  }

  const currentPhoto = photos[currentIndex];

  return (
    <div className="bg-black min-h-screen overflow-hidden flex items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.div
          key={currentPhoto.id}
          initial={{ opacity: 0, scale: 1.02 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5, ease: "easeInOut" }}
          className="relative w-full h-screen"
        >
          <Image
            src={currentPhoto.display_url || currentPhoto.url}
            alt="Wedding Photo"
            fill
            className="object-contain"
            priority
          />
          {currentIndex === 0 && photos.length > 1 && (
             <div className="absolute top-10 left-10 bg-white/10 backdrop-blur-md text-white px-6 py-3 rounded-full font-medium tracking-widest text-sm uppercase shadow-2xl border border-white/20">
                Just Captured
             </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
