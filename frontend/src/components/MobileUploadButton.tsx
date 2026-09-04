'use client';

import { useState, useRef } from 'react';
import { Camera, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function MobileUploadButton({ weddingSlug }: { weddingSlug: string }) {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    
    const formData = new FormData();
    formData.append('photo', file);

    try {
      const response = await fetch(`/api/weddings/${weddingSlug}/photos/upload/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload');
      }
      
      // Successfully uploaded! The WebSocket will handle adding it to the gallery.
    } catch (error) {
      console.error('Error uploading photo:', error);
      alert('Failed to upload photo. Please try again.');
    } finally {
      setIsUploading(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <input
        type="file"
        accept="image/*"
        capture="environment"
        ref={fileInputRef}
        onChange={handleCapture}
        className="hidden"
      />
      
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="fixed bottom-6 right-6 h-14 px-6 rounded-full bg-white text-neutral-950 flex items-center justify-center shadow-[0_0_40px_rgba(255,255,255,0.3)] hover:scale-105 active:scale-95 transition-all z-50 font-semibold tracking-wider gap-3 disabled:opacity-80 disabled:hover:scale-100"
      >
        {isUploading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Camera className="w-5 h-5" />
        )}
        {isUploading ? 'UPLOADING...' : 'ADD PHOTO'}
      </button>
    </>
  );
}
