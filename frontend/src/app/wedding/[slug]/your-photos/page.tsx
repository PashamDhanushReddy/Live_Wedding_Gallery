'use client';

import { useState, use } from 'react';
import { Camera, CheckCircle2, Circle, ScanFace, Check, Download, Share2 } from 'lucide-react';
import Gallery from '@/components/Gallery';
import { motion } from 'framer-motion';
import Header from '@/components/Header';
import Stepper from '@/components/Stepper';

export default function YourPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [step, setStep] = useState<'capture' | 'processing' | 'results'>('capture');
  const [session, setSession] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [processState, setProcessState] = useState(0);

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImagePreview(URL.createObjectURL(file));
      setStep('processing');
      
      setTimeout(() => setProcessState(1), 1000);
      setTimeout(() => setProcessState(2), 2500);
      setTimeout(() => {
        setProcessState(3);
        setTimeout(() => {
          setSession('mock-session-123');
          setStep('results');
        }, 800);
      }, 4000);
    }
  };

  const handleDownloadAll = () => {
    console.log("Downloading all photos...");
  };

  const handleShare = () => {
    console.log("Sharing gallery...");
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)] flex flex-col pt-20">
      <Header weddingSlug={slug} />
      
      <div className="w-full max-w-6xl mx-auto px-4 py-8 flex-1 flex flex-col">
        <Stepper currentStep={step} />

        {step === 'capture' && (
          <div className="flex-1 flex flex-col md:flex-row items-center justify-center gap-12 md:gap-24 max-w-5xl mx-auto w-full">
            {/* Left side text (Desktop) / Top text (Mobile) */}
            <div className="flex-1 text-center md:text-left">
              <h2 className="font-serif text-3xl md:text-4xl mb-4 text-neutral-900">Take a Selfie</h2>
              <p className="text-neutral-500 text-sm md:text-base max-w-[280px] md:max-w-md mx-auto md:mx-0 mb-8 leading-relaxed">
                We'll find photos where you appear using face matching.
              </p>

              {/* Instructions list (Hidden on mobile, visible on md) */}
              <div className="hidden md:flex flex-col gap-4">
                <div className="flex items-center gap-3 text-neutral-600">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  <span className="text-sm">Make sure your face is clearly visible</span>
                </div>
                <div className="flex items-center gap-3 text-neutral-600">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  <span className="text-sm">Good lighting helps better results</span>
                </div>
                <div className="flex items-center gap-3 text-neutral-600">
                  <Circle className="w-5 h-5 text-neutral-300" />
                  <span className="text-sm">We don't store or share your selfie</span>
                </div>
              </div>
            </div>

            {/* Right side scanner (Desktop) / Bottom scanner (Mobile) */}
            <div className="flex-1 flex flex-col items-center w-full max-w-[320px]">
              <div className="relative w-full aspect-[4/5] bg-neutral-100 rounded-[32px] overflow-hidden flex items-center justify-center shadow-inner mb-6">
                <div className="absolute inset-4 border-2 border-transparent border-t-white border-l-white rounded-tl-[24px] w-12 h-12 z-10 opacity-70" />
                <div className="absolute inset-4 right-4 left-auto border-2 border-transparent border-t-white border-r-white rounded-tr-[24px] w-12 h-12 z-10 opacity-70" />
                <div className="absolute inset-4 bottom-4 top-auto border-2 border-transparent border-b-white border-l-white rounded-bl-[24px] w-12 h-12 z-10 opacity-70" />
                <div className="absolute inset-4 bottom-4 top-auto right-4 left-auto border-2 border-transparent border-b-white border-r-white rounded-br-[24px] w-12 h-12 z-10 opacity-70" />
                
                {imagePreview ? (
                  <img src={imagePreview} className="w-full h-full object-cover" alt="Preview" />
                ) : (
                  <div className="text-neutral-300">
                    <ScanFace className="w-16 h-16" />
                  </div>
                )}
                <input type="file" accept="image/*" capture="user" onChange={handleUpload} className="absolute inset-0 opacity-0 cursor-pointer z-20" />
              </div>

              <button className="w-full bg-[var(--color-brand)] text-white font-medium py-4 rounded-full flex items-center justify-center gap-3 active:scale-95 transition-transform shadow-lg shadow-brand/20 relative overflow-hidden">
                <Camera className="w-5 h-5" />
                Capture Photo
                <input type="file" accept="image/*" capture="user" onChange={handleUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
              </button>
            </div>
          </div>
        )}

        {step === 'processing' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center w-full max-w-md mx-auto">
            <div className="relative mb-10">
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
            
            <h2 className="font-serif text-3xl mb-2">Finding your photos...</h2>
            <p className="text-neutral-500 text-sm mb-12">This may take a few seconds.</p>

            <div className="w-full max-w-[280px] space-y-5 text-left bg-white p-6 rounded-2xl shadow-sm border border-neutral-100">
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

            <div className="mt-12">
              <div className="text-[var(--color-brand)] text-center text-sm mb-1">♥</div>
              <p className="font-serif italic text-neutral-400">"Good things take a moment"</p>
            </div>
          </div>
        )}

        {step === 'results' && (
          <div className="flex-1 flex flex-col w-full max-w-6xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
              <div>
                <h2 className="font-serif text-3xl mb-2">Your Photos</h2>
                <p className="text-neutral-500 text-sm mb-4">Here are the photos where you appear</p>
                <div className="inline-block bg-[var(--color-brand-light)] text-[var(--color-brand-dark)] px-4 py-1.5 rounded-full text-xs font-medium tracking-wide">
                  32 photos found
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <button onClick={handleDownloadAll} className="flex-1 sm:flex-none bg-neutral-900 text-white px-5 py-2.5 rounded-full text-sm font-medium flex items-center justify-center gap-2 hover:bg-neutral-800 transition-colors">
                  <Download className="w-4 h-4" />
                  Download All
                </button>
                <button onClick={handleShare} className="flex-1 sm:flex-none bg-neutral-100 text-neutral-900 px-5 py-2.5 rounded-full text-sm font-medium flex items-center justify-center gap-2 hover:bg-neutral-200 transition-colors">
                  <Share2 className="w-4 h-4" />
                  Share
                </button>
              </div>
            </div>
            
            <Gallery initialPhotos={[]} weddingSlug={slug} sessionId={session} />
          </div>
        )}
      </div>
    </div>
  );
}
