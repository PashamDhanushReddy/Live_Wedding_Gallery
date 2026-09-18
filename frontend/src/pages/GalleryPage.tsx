import { useState, useEffect } from "react";
import { Loader2, Calendar, MapPin, Heart, Grid, Crown } from "lucide-react";
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

import bgImage from "../assets/bg_blue.png";
import mobileBg from "../assets/mobile_bg.png";

export default function GalleryPage() {
  const [activeTab, setActiveTab] = useState("All");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  
  const tabs = [
    "All",
    "Bride",
    "Groom",
    "Bride and Groom",
    "Engagement",
    "Pre-wedding Shoot",
    "Haldi",
    "Before Wedding Rituals",
    "Wedding Day",
    "Uncategorized"
  ];

  useEffect(() => {
    // 1. Fetch initial photos
    const fetchPhotos = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          // Backend returns serializer data. Map it.
          const mappedPhotos = data.map((p: any) => ({
            id: p.id,
            url: p.secure_url || p.cloudinary_url || "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800",
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: p.folder || "Uncategorized"
          }));
          setPhotos(mappedPhotos);
        }
      } catch (err) {
        console.error("Failed to fetch photos", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPhotos();

    // 2. Polling every 5 seconds for reliable real-time updates
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          const mappedPhotos = data.map((p: any) => ({
            id: p.id,
            url: p.secure_url || p.cloudinary_url || "",
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: p.folder || "Uncategorized"
          }));
          setPhotos(prev => {
            // Compare lengths. We can't just check if length changed for deletions,
            // but it's safe to just set mappedPhotos since it's the source of truth
            return mappedPhotos;
          });
        }
      } catch (_) {}
    }, 5000);

    // 3. WebSocket for instant push updates (bonus speed)
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_BASE_URL}/weddings/${WEDDING_SLUG}/`);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_photo') {
          const p = data.photo;
          const newPhoto = {
            id: p.id,
            url: p.secure_url || p.cloudinary_url,
            thumbnail_url: p.thumbnail_url,
            aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-square",
            category: p.folder || "Uncategorized"
          };
          setPhotos((prev) => {
            if (prev.find(x => x.id === newPhoto.id)) return prev;
            return [newPhoto, ...prev];
          });
        } else if (data.type === 'delete_photo') {
          setPhotos(prev => prev.filter(p => p.id !== data.photo_id));
        }
      };
    } catch (_) {}

    return () => {
      clearInterval(pollInterval);
      ws?.close();
    };

  }, []);

  const openLightbox = (index: number) => {
    setCurrentPhotoIndex(index);
    setLightboxOpen(true);
  };

  const filteredPhotos = activeTab === "All" ? photos : photos.filter(p => p.category === activeTab);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#fffaf7] to-[#fcfaf8] pb-12">
      {/* Header Wrapper with Restricted Background */}
      <div className="relative w-full z-10 pt-16 md:pt-24 pb-4">
        
        {/* User's Exact Floral Background Image for Desktop */}
        <div 
          className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-50 -z-10 pointer-events-none [mask-image:linear-gradient(to_bottom,white_80%,transparent_100%)] hidden md:block"
          style={{ backgroundImage: `url(${bgImage})` }}
        ></div>

        {/* User's Exact Floral Background Image for Mobile */}
        <div 
          className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-50 -z-10 pointer-events-none [mask-image:linear-gradient(to_bottom,white_80%,transparent_100%)] block md:hidden"
          style={{ backgroundImage: `url(${mobileBg})` }}
        ></div>

        <div className="container mx-auto px-4 md:px-8 max-w-7xl">
          {/* Header section */}
          <div className="text-center mb-2">
            <p className="text-[9px] md:text-[10px] font-semibold tracking-[0.3em] text-[#554c4c] uppercase mb-2 md:mb-3">
              The Wedding Of
            </p>
            <h1 className="text-4xl md:text-5xl font-serif text-[#2d2626] mb-0 leading-tight">
              <span className="block whitespace-nowrap">Sandeep Reddy</span>
              <span className="block italic text-3xl md:text-4xl text-[#b36c73] font-serif my-0.5 md:my-1 flex items-center justify-center gap-3 md:gap-4">
                <span className="w-12 md:w-16 h-[1px] bg-border/80"></span>
                &amp;
                <span className="w-12 md:w-16 h-[1px] bg-border/80"></span>
              </span>
              <span className="block whitespace-nowrap">Prathyusha Reddy</span>
            </h1>
            
            <p className="font-script text-xl md:text-2xl text-[#a07171] mb-4 md:mb-6 mt-1 md:mt-2 px-2 leading-tight">Two Hearts &middot; One Journey &middot; Forever Together</p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-6 text-[13px] text-[#554c4c] font-medium mb-6 md:mb-8">
              <span className="flex items-center gap-2 whitespace-nowrap"><Calendar className="w-3.5 h-3.5 text-[#a07171]" /> November 21, 2026</span>
              <span className="hidden sm:block w-px h-4 bg-border"></span>
              <span className="flex items-center gap-2 whitespace-nowrap"><MapPin className="w-3.5 h-3.5 text-[#a07171]" /> Nizamabad, Telangana</span>
            </div>
            
            {/* Torn paper / rounded box */}
            <div className="mx-auto max-w-2xl bg-white/70 backdrop-blur-md rounded-2xl md:rounded-3xl p-5 md:p-8 shadow-[0_4px_20px_rgba(0,0,0,0.03)] mb-6 md:mb-8 border border-white/50">
              <p className="text-[#554c4c] font-serif text-sm md:text-lg leading-relaxed mb-3 md:mb-4">
                A celebration of love, family and beautiful moments. <br className="hidden md:block"/>
                Join us in reliving the memories of our special day.
              </p>
              <div className="flex items-center justify-center gap-3">
                <div className="h-px w-8 bg-border"></div>
                <Heart className="w-2.5 h-2.5 text-[#b36c73] fill-[#b36c73]" />
                <div className="h-px w-8 bg-border"></div>
              </div>
            </div>
            
            <div className="mt-6 flex justify-center">
               <div className="bg-[#fcf5f1] rounded-full px-5 py-2.5 flex items-center gap-3 md:gap-4 border border-[#f0e4dc] shadow-sm">
                  <div className="flex items-center gap-1.5 text-[#e03131] text-[11px] font-bold tracking-wider">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#e03131] opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-[#e03131]"></span>
                    </span>
                    LIVE
                  </div>
                  <div className="w-px h-4 bg-[#e6d8d0]"></div>
                  <p className="text-xs md:text-sm font-medium text-[#554c4c]">
                    <strong className="text-[#2d2626] font-semibold">{photos.length}</strong> photos and counting...
                  </p>
               </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Container below Header */}
      <div className="container mx-auto px-4 md:px-8 max-w-7xl relative z-10 pt-0">
      
      {/* Filters and Controls */}
      <div className="flex justify-center mb-4 w-full">
        <div className="flex overflow-x-auto pb-2 hide-scrollbar gap-2 px-4 max-w-full">
          {tabs.map((tab) => {
             let Icon = null;
             if (tab === "All") Icon = Grid;
             else if (tab === "Bride") Icon = Crown;
             else if (tab === "Groom") Icon = BowTieIcon;
             else if (tab === "Bride and Groom") Icon = Heart;
             
             return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-[11px] md:text-xs font-medium whitespace-nowrap transition-all duration-300 shadow-sm border ${
                  activeTab === tab 
                    ? "bg-[#a67272] text-white border-[#a67272]" 
                    : "bg-[#fcf5f1] text-[#554c4c] border-[#f0e4dc] hover:bg-[#f4ebe6]"
                }`}
              >
                {Icon && <Icon className="w-4 h-4" />}
                {tab === "Bride and Groom" ? "Bride & Groom" : tab}
              </button>
             );
          })}
        </div>
      </div>
      
      {/* Masonry Grid */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredPhotos.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          No photos found for this category yet.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4">
          {filteredPhotos.map((photo, index) => (
            <div 
              key={photo.id} 
              onClick={() => openLightbox(index)}
              className="cursor-pointer group relative rounded-xl overflow-hidden shadow-sm aspect-[4/3]"
            >
              <img 
                src={photo.thumbnail_url || photo.url} 
                alt={photo.category} 
                className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                <p className="text-white font-medium">View Photo</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {lightboxOpen && (
        <PhotoLightbox 
          photos={filteredPhotos} 
          initialIndex={currentPhotoIndex} 
          onClose={() => setLightboxOpen(false)} 
        />
      )}
      </div>
    </div>
  );
}

function BowTieIcon({ className }: { className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width="24" height="24" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="m20.2 6.3-5 2.2a3 3 0 0 0-1.6 1.9l-.6 2.6a2 2 0 0 1-3.6 0l-.6-2.6a3 3 0 0 0-1.6-1.9l-5-2.2A1 1 0 0 0 1 7.2v9.6a1 1 0 0 0 1.4.9l5-2.2a3 3 0 0 0 1.6-1.9l.6-2.6a2 2 0 0 1 3.6 0l.6 2.6a3 3 0 0 0 1.6 1.9l5 2.2a1 1 0 0 0 1.4-.9V7.2a1 1 0 0 0-1.4-.9Z"/>
    </svg>
  );
}
