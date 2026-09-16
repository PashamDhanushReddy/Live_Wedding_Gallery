import { useState, useEffect } from "react";
import { UploadCloud, Upload, Camera, Lock, Eye, ScanFace } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";


import PhotoLightbox from "../components/PhotoLightbox";
import { API_BASE_URL, WS_BASE_URL, WEDDING_SLUG } from "../config";

interface Photo {
  id: number;
  url: string;
  secure_url?: string;
  thumbnail_url?: string;
  aspect?: string;
  category?: string;
}

export default function FindPhotosPage() {
  const [step, setStep] = useState<"upload" | "processing" | "results">("upload");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [matchedPhotos, setMatchedPhotos] = useState<Photo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (step !== "results") return;

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_BASE_URL}/weddings/${WEDDING_SLUG}/`);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_photo') {
          // Silent refresh of matches when a new photo arrives
          handleUploadClick(true);
        } else if (data.type === 'delete_photo') {
          // Remove deleted photo from matches
          setMatchedPhotos(prev => prev.filter(p => p.id !== data.photo_id));
        }
      };
    } catch (_) {}

    return () => {
      ws?.close();
    };
  }, [step]);

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadClick = async (silent = false) => {
    if (!selectedFile) return;
    
    if (!silent) {
      setStep("processing");
      setError(null);
    }
    
    const formData = new FormData();
    formData.append("file", selectedFile);
    
    try {
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/search/`, {
        method: "POST",
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || "Failed to search photos");
      }
      
      const mappedPhotos = data.photos.map((p: any) => ({
        id: p.id,
        url: p.secure_url || p.cloudinary_url,
        thumbnail_url: p.thumbnail_url,
        aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
      }));
      
      setMatchedPhotos(mappedPhotos);
      setStep("results");
    } catch (err: any) {
      console.error(err);
      setError(err.message);
      setStep("upload");
    }
  };

  const [progress, setProgress] = useState(0);

  // Simulated progress animation when in "processing" state
  useEffect(() => {
    if (step === "processing") {
      setProgress(0);
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev < 30) return prev + Math.floor(Math.random() * 10) + 5;
          if (prev < 70) return prev + Math.floor(Math.random() * 5) + 2;
          if (prev < 98) return prev + 1;
          return 98;
        });
      }, 200);
      return () => clearInterval(interval);
    }
  }, [step]);

  return (
    <div className="flex flex-col md:flex-row min-h-[calc(100vh-5rem)] bg-background">
      {/* Left side Image - Hidden on mobile results page to save space */}
      <div className={`w-full md:w-1/3 lg:w-2/5 h-64 md:h-auto relative ${step === 'results' ? 'hidden md:block' : ''}`}>
        <img 
          src="https://images.unsplash.com/photo-1519225421980-715cb0215aed?auto=format&fit=crop&q=80&w=1200" 
          alt="Couple smiling" 
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex flex-col justify-end p-8">
          <p className="text-white font-serif italic text-4xl mb-2">Every guest</p>
          <p className="text-white font-serif text-3xl mb-4">has a story here</p>
          <div className="w-8 h-px bg-white/50 mb-4"></div>
          <p className="text-white/80 text-sm">Find the moments where you belong</p>
        </div>
      </div>

      {/* Right side content */}
      <div className="flex-1 p-6 md:p-12 flex flex-col items-center justify-center relative overflow-y-auto">
        <AnimatePresence mode="wait">
          {step === "upload" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full max-w-lg"
            >
              <div className="text-center mb-10">
                <h1 className="text-4xl font-serif text-foreground mb-3">Find Your Memories</h1>
                <p className="text-muted-foreground">Upload a selfie and we'll find wedding photos containing you.</p>
              </div>

              <div className="bg-white rounded-2xl shadow-sm border border-border overflow-hidden">
                <div className="flex border-b border-border">
                  <button className="flex-1 py-4 flex items-center justify-center gap-2 font-medium text-primary border-b-2 border-primary bg-secondary/30">
                    <UploadCloud className="w-5 h-5" />
                    Upload Selfie
                  </button>
                  <button className="flex-1 py-4 flex items-center justify-center gap-2 font-medium text-muted-foreground hover:bg-secondary/50">
                    <Camera className="w-5 h-5" />
                    Take a Photo
                  </button>
                </div>

                <div className="p-8">
                  <div className="border-2 border-dashed border-primary/30 rounded-3xl p-12 bg-white/50 backdrop-blur-sm relative overflow-hidden group">
                    <input 
                      type="file" 
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handleFileSelect}
                    />
                    
                    <div className="flex flex-col items-center text-center space-y-4">
                      <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                        <Upload className="w-8 h-8 text-primary" />
                      </div>
                      
                      <div>
                        <h3 className="text-xl font-serif text-foreground mb-2">
                          {selectedFile ? selectedFile.name : "Tap to upload or take a selfie"}
                        </h3>
                        <p className="text-muted-foreground text-sm">
                          Supports JPG, PNG, WEBP (Max 10MB)
                        </p>
                      </div>
                      
                      {error && (
                        <div className="text-red-500 text-sm mt-4 bg-red-50 px-4 py-2 rounded-lg">
                          {error}
                        </div>
                      )}

                      <button 
                        onClick={() => handleUploadClick(false)}
                        disabled={!selectedFile}
                        className="mt-6 bg-primary text-primary-foreground px-8 py-3 rounded-full font-medium hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed relative z-20"
                      >
                        Find My Photos
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-12 flex justify-between gap-4 text-center">
                <div className="flex-1">
                  <div className="w-12 h-12 mx-auto bg-secondary rounded-full flex items-center justify-center text-primary mb-3">
                    <ScanFace className="w-6 h-6" />
                  </div>
                  <h3 className="font-medium text-sm">AI Face Detection</h3>
                  <p className="text-xs text-muted-foreground">Accurate and secure</p>
                </div>
                <div className="flex-1">
                  <div className="w-12 h-12 mx-auto bg-secondary rounded-full flex items-center justify-center text-primary mb-3">
                    <Lock className="w-6 h-6" />
                  </div>
                  <h3 className="font-medium text-sm">Your Privacy</h3>
                  <p className="text-xs text-muted-foreground">We don't store your selfie</p>
                </div>
                <div className="flex-1">
                  <div className="w-12 h-12 mx-auto bg-secondary rounded-full flex items-center justify-center text-primary mb-3">
                    <Eye className="w-6 h-6" />
                  </div>
                  <h3 className="font-medium text-sm">Only Your Photos</h3>
                  <p className="text-xs text-muted-foreground">See your memories</p>
                </div>
              </div>
            </motion.div>
          )}

          {step === "processing" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="w-full max-w-lg text-center"
            >
              <div className="w-20 h-20 mx-auto text-primary mb-6 animate-pulse">
                <ScanFace className="w-full h-full" />
              </div>
              <h2 className="text-3xl font-serif text-foreground mb-3">Finding Your Memories...</h2>
              <p className="text-muted-foreground mb-12">Please wait while we analyze your selfie and search for your photos.</p>

              <div className="bg-white p-8 rounded-2xl shadow-sm border border-border text-left">
                <div className="flex items-center gap-6 mb-8">
                  <div className="relative w-24 h-24">
                    <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 36 36">
                      <path className="text-secondary stroke-current" strokeWidth="3" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                      <path className="text-primary stroke-current transition-all duration-300 ease-out" strokeWidth="3" strokeDasharray={`${progress}, 100`} fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center font-medium text-xl">{progress}%</div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg text-foreground">Analyzing your selfie</h3>
                    <p className="text-sm text-muted-foreground">Detecting face and creating face embedding...<br/>This may take a few seconds.</p>
                  </div>
                </div>

                <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
                  {/* Timeline items can go here for more detail */}
                </div>
              </div>
            </motion.div>
          )}

          {step === "results" && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-4xl mx-auto"
            >
              <div className="flex justify-between items-end mb-8">
                <div>
                  <h2 className="text-3xl font-serif text-foreground mb-2">We found you!</h2>
                  <p className="text-muted-foreground">Found {matchedPhotos.length} photos containing your face</p>
                </div>
                <button 
                  onClick={() => {
                    setStep("upload");
                    setSelectedFile(null);
                    setMatchedPhotos([]);
                  }}
                  className="text-primary font-medium hover:underline flex items-center gap-2"
                >
                  <ScanFace className="w-4 h-4" />
                  Search another face
                </button>
              </div>

              {/* Gallery Grid */}
              <div className="columns-2 md:columns-3 gap-4 space-y-4">
                {matchedPhotos.map((photo, index) => (
                  <div 
                    key={photo.id} 
                    onClick={() => openLightbox(index)}
                    className="break-inside-avoid rounded-xl overflow-hidden shadow-sm cursor-pointer group relative"
                  >
                    <img 
                      src={photo.thumbnail_url || photo.url} 
                      className="w-full object-cover group-hover:scale-105 transition-transform duration-500"
                      style={{ 
                        aspectRatio: photo.aspect?.replace('aspect-[', '').replace(']', '') || 'auto'
                      }}
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                      <p className="text-white font-medium">View Photo</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {lightboxOpen && (
        <PhotoLightbox 
          photos={matchedPhotos} 
          initialIndex={currentPhotoIndex} 
          onClose={() => setLightboxOpen(false)} 
        />
      )}
    </div>
  );
}
