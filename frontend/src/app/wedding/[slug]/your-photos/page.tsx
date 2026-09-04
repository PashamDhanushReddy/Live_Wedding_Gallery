'use client';

import { useState, use } from 'react';
import { Camera, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import Gallery from '@/components/Gallery';

export default function YourPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const [consentGiven, setConsentGiven] = useState(false);
  const [session, setSession] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setIsUploading(true);
      // In a real implementation, we would send this to the Django API
      // e.g. POST /api/weddings/{slug}/guest/register/
      setTimeout(() => {
        setIsUploading(false);
        setSession('mock-session-123'); // Store session ID
      }, 1500);
    }
  };

  if (!consentGiven) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-6 text-white">
        <div className="max-w-md w-full bg-neutral-900 border border-white/10 rounded-2xl p-8 space-y-6">
          <div className="flex justify-center">
            <div className="h-16 w-16 bg-white/5 rounded-full flex items-center justify-center">
              <ShieldCheck className="w-8 h-8 text-neutral-300" />
            </div>
          </div>
          <h2 className="text-2xl font-semibold text-center tracking-wider">Privacy & Consent</h2>
          <p className="text-neutral-400 text-sm text-center leading-relaxed">
            Your selfie will be processed securely to find photos from this wedding that may contain you.
            Your selfie and face data will <strong className="text-white">not</strong> be publicly displayed or shared.
          </p>
          <div className="pt-4 space-y-3">
            <button 
              onClick={() => setConsentGiven(true)}
              className="w-full bg-white text-black font-semibold py-3 rounded-lg hover:bg-neutral-200 transition-colors uppercase tracking-widest text-sm"
            >
              I Agree
            </button>
            <Link 
              href={`/wedding/${slug}`}
              className="w-full block text-center bg-transparent text-neutral-500 font-semibold py-3 rounded-lg hover:text-white hover:bg-white/5 transition-colors uppercase tracking-widest text-sm"
            >
              Cancel
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-6 text-white">
        <div className="max-w-md w-full space-y-8 text-center">
          <div className="space-y-4">
            <h2 className="text-3xl font-light tracking-widest uppercase">Selfie Match</h2>
            <p className="text-neutral-400 text-sm">Take a photo to find your matches.</p>
          </div>
          
          <div className={`relative aspect-[3/4] w-full bg-neutral-900 rounded-2xl border-2 border-dashed ${isUploading ? 'border-white/50 bg-neutral-800' : 'border-white/20'} flex flex-col items-center justify-center gap-4 hover:border-white/50 hover:bg-neutral-800 transition-all cursor-pointer overflow-hidden`}>
             {!isUploading && <input type="file" accept="image/*" capture="user" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleUpload} />}
             
             {isUploading ? (
                <div className="animate-pulse flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full border-4 border-white/20 border-t-white animate-spin mb-4" />
                    <p className="text-sm tracking-widest uppercase text-white">Processing...</p>
                </div>
             ) : (
                <>
                    <Camera className="w-12 h-12 text-neutral-500" />
                    <p className="text-sm font-medium tracking-widest uppercase text-neutral-500">Tap to capture</p>
                </>
             )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center text-center text-white p-10">
      <h2 className="text-3xl font-light tracking-widest uppercase mb-4">Finding Matches</h2>
      <p className="text-neutral-400 max-w-md">We are currently scanning the live feed. Photos containing you will appear here automatically.</p>
      <div className="mt-12 flex justify-center w-full">
         <div className="w-64 h-1 bg-neutral-900 rounded-full overflow-hidden relative">
            <div className="absolute top-0 left-0 h-full bg-white/30 w-1/3 animate-[pulse_2s_ease-in-out_infinite] translate-x-[200%] transition-transform duration-1000"></div>
         </div>
      </div>
      
      <div className="w-full mt-12 text-left">
         <Gallery initialPhotos={[]} weddingSlug={slug} sessionId={session} />
      </div>
    </div>
  );
}
