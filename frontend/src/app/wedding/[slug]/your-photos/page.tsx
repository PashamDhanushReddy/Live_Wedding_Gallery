'use client';

import { useState, use, useEffect, useRef } from 'react';
import { Camera, Lock, CheckCircle2, Circle, ChevronLeft, ScanFace } from 'lucide-react';
import Link from 'next/link';
import Gallery from '@/components/Gallery';
import { motion } from 'framer-motion';

export default function YourPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [step, setStep] = useState<'capture' | 'processing' | 'results'>('capture');
  const [session, setSession] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  
  // Simulated processing steps
  const [processState, setProcessState] = useState(0);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImagePreview(URL.createObjectURL(file));
      setStep('processing');
      
      // Simulate steps
      setTimeout(() => setProcessState(1), 1000); // Processing selfie
      setTimeout(() => setProcessState(2), 2500); // Matching
      
      // In a real implementation, upload to Django
      setTimeout(() => {
        setProcessState(3); // Almost there
        setTimeout(() => {
          setSession('mock-session-123');
          setStep('results');
        }, 800);
      }, 4000);
    }
  };

  const TopBar = ({ title }: { title: string }) => (
    <div className="flex items-center p-6 bg-[var(--color-background)] sticky top-0 z-10 border-b border-black/5">
      <Link href={`/wedding/${slug}`} className="p-2 -ml-2 text-neutral-500 hover:bg-neutral-100 rounded-full transition-colors">
        <ChevronLeft className="w-6 h-6" />
      </Link>
      <h1 className="flex-1 text-center font-serif text-xl mr-8">{title}</h1>
    </div>
  );

  if (step === 'capture') {
    return (
      <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
        <TopBar title="Find Your Photos" />
        
        <div className="flex-1 flex flex-col items-center p-6 text-center max-w-md mx-auto w-full">
          <div className="mt-8 mb-6 h-16 w-16 bg-[var(--color-brand-light)] rounded-full flex items-center justify-center">
            <Camera className="w-8 h-8 text-[var(--color-brand)]" />
          </div>
          
          <h2 className="font-serif text-3xl mb-3">Take a Selfie</h2>
          <p className="text-neutral-500 text-sm max-w-[280px] mb-10">
            We'll find photos where you appear using face matching.
          </p>

          {/* Scanner UI */}
          <div className="relative w-full aspect-[4/5] max-w-[300px] mb-8 bg-neutral-100 rounded-2xl overflow-hidden flex items-center justify-center">
            {/* Corner brackets */}
            <div className="absolute inset-4 border-2 border-transparent border-t-white border-l-white rounded-tl-3xl w-12 h-12 z-10 opacity-70" />
            <div className="absolute inset-4 right-4 left-auto border-2 border-transparent border-t-white border-r-white rounded-tr-3xl w-12 h-12 z-10 opacity-70" />
            <div className="absolute inset-4 bottom-4 top-auto border-2 border-transparent border-b-white border-l-white rounded-bl-3xl w-12 h-12 z-10 opacity-70" />
            <div className="absolute inset-4 bottom-4 top-auto right-4 left-auto border-2 border-transparent border-b-white border-r-white rounded-br-3xl w-12 h-12 z-10 opacity-70" />
            
            {imagePreview ? (
              <img src={imagePreview} className="w-full h-full object-cover" alt="Preview" />
            ) : (
              <div className="text-neutral-300">
                <ScanFace className="w-16 h-16" />
              </div>
            )}

            <input 
              type="file" 
              accept="image/*" 
              capture="user" 
              onChange={handleUpload}
              className="absolute inset-0 opacity-0 cursor-pointer z-20" 
            />
          </div>

          <button className="w-full bg-[var(--color-brand)] text-white font-medium py-4 rounded-2xl flex items-center justify-center gap-3 active:scale-95 transition-transform shadow-lg shadow-brand/20 relative overflow-hidden group">
            <Camera className="w-5 h-5" />
            Capture Photo
            <input 
              type="file" 
              accept="image/*" 
              capture="user" 
              onChange={handleUpload}
              className="absolute inset-0 opacity-0 cursor-pointer" 
            />
          </button>

          <div className="mt-8 flex items-start gap-3 text-left max-w-[280px]">
            <Lock className="w-4 h-4 text-neutral-400 mt-1 flex-shrink-0" />
            <p className="text-xs text-neutral-500 leading-relaxed">
              Your selfie is only used to find your photos. We do not store or share it.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'processing') {
    return (
      <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
        <TopBar title="Find Your Photos" />
        
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto w-full">
          <div className="relative mb-12">
            <svg className="w-32 h-32 text-neutral-200" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="4" />
              <motion.circle 
                cx="50" cy="50" r="45" fill="none" 
                stroke="var(--color-brand)" 
                strokeWidth="4" 
                strokeDasharray="283"
                initial={{ strokeDashoffset: 283 }}
                animate={{ strokeDashoffset: 0 }}
                transition={{ duration: 4, ease: "linear" }}
                strokeLinecap="round"
                className="origin-center -rotate-90"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center text-[var(--color-brand)]">
              <ScanFace className="w-10 h-10" />
            </div>
          </div>
          
          <h2 className="font-serif text-2xl mb-2">Finding your photos...</h2>
          <p className="text-neutral-500 text-sm mb-12">This may take a few seconds.</p>

          <div className="w-full max-w-[280px] space-y-4 text-left">
            <div className="flex items-center gap-4">
              {processState >= 1 ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <Circle className="w-5 h-5 text-neutral-300" />}
              <span className={`text-sm ${processState >= 1 ? 'text-neutral-900 font-medium' : 'text-neutral-500'}`}>Processing your selfie</span>
            </div>
            <div className="flex items-center gap-4">
              {processState >= 2 ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <Circle className="w-5 h-5 text-neutral-300" />}
              <span className={`text-sm ${processState >= 2 ? 'text-neutral-900 font-medium' : 'text-neutral-500'}`}>Matching with wedding photos</span>
            </div>
            <div className="flex items-center gap-4">
              {processState >= 3 ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <Circle className="w-5 h-5 text-neutral-300" />}
              <span className={`text-sm ${processState >= 3 ? 'text-neutral-900 font-medium' : 'text-neutral-500'}`}>Almost there...</span>
            </div>
          </div>

          <div className="mt-auto pt-12 pb-6">
            <div className="text-[var(--color-brand)] text-center text-sm mb-2">♥</div>
            <p className="font-serif italic text-neutral-400">"Every face tells a story"</p>
          </div>
        </div>
      </div>
    );
  }

  // Results step
  return (
    <div className="min-h-screen bg-[var(--color-background)] flex flex-col">
      <TopBar title="Your Photos" />
      
      <div className="flex flex-col items-center text-center p-6">
        <p className="text-neutral-600 text-sm mb-4">Here are the photos where you appear</p>
        
        {/* Placeholder count until websocket connects */}
        <div className="bg-[var(--color-brand-light)] text-[var(--color-brand-dark)] px-4 py-1.5 rounded-full text-xs font-medium tracking-wide">
          Scanning live feed...
        </div>
      </div>
      
      <div className="flex-1 w-full pb-8">
         <Gallery initialPhotos={[]} weddingSlug={slug} sessionId={session} />
      </div>
    </div>
  );
}
