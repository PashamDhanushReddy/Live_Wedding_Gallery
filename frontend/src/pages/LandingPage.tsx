import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Camera, Image as ImageIcon, Users, Infinity } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../config";

export default function LandingPage() {
  const [photoCount, setPhotoCount] = useState<number | null>(null);

  useEffect(() => {
    const fetchPhotoCount = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photos/`);
        if (res.ok) {
          const data = await res.json();
          setPhotoCount(data.length || 0);
        }
      } catch (err) {
        console.error("Failed to fetch photo count", err);
      }
    };
    fetchPhotoCount();
  }, []);

  return (
    <div className="flex flex-col md:flex-row min-h-[calc(100vh-5rem)]">
      {/* Left side content overlaid on mobile, side-by-side on desktop */}
      <div className="relative w-full md:w-1/2 bg-background flex flex-col justify-center p-8 md:p-16 lg:p-24 z-10">
        <div className="max-w-md">
          <p className="text-sm tracking-widest uppercase text-muted-foreground mb-4">
            Together Forever <span className="inline-block w-8 h-px bg-muted-foreground align-middle ml-2"></span>
          </p>
          
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-serif text-foreground mb-4 leading-tight">
            <span className="block whitespace-nowrap">Sandeep Reddy</span>
            <span className="block italic text-4xl md:text-5xl lg:text-6xl text-primary font-serif my-2">&amp;</span>
            <span className="block whitespace-nowrap">Prathyusha</span>
          </h1>
          
          <div className="text-muted-foreground mt-6 space-y-1">
            <p className="font-medium text-foreground">November 21, 2026</p>
            <p>Hyderabad, Telangana</p>
          </div>
          
          <div className="w-8 h-px bg-border my-6"></div>
          
          <p className="text-muted-foreground mb-10 leading-relaxed">
            A celebration of love, family and beautiful moments. 
            Join us in reliving the memories of our special day.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 mb-16">
            <Link 
              to="/photos" 
              className="flex items-center justify-center gap-2 bg-primary text-primary-foreground px-8 py-4 rounded-full font-medium hover:bg-primary/90 transition-all shadow-md"
            >
              <Camera className="w-5 h-5" />
              View All Photos
            </Link>
            <Link 
              to="/find" 
              className="flex items-center justify-center gap-2 bg-transparent border border-foreground/20 text-foreground px-8 py-4 rounded-full font-medium hover:bg-secondary transition-all"
            >
              <ImageIcon className="w-5 h-5" />
              Find My Photos
            </Link>
          </div>

          {/* Stats Bar */}
          <div className="flex items-center justify-between border-t border-border/50 pt-8 mt-auto">
            <div className="text-center">
              <ImageIcon className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
              <p className="font-semibold text-lg">{photoCount !== null ? photoCount : "..."}</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Photos</p>
            </div>
            <div className="w-px h-12 bg-border/50"></div>
            <div className="text-center">
              <HeartIcon className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
              <p className="font-semibold text-lg">1</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Beautiful Day</p>
            </div>
            <div className="w-px h-12 bg-border/50"></div>
            <div className="text-center">
              <Users className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
              <p className="font-semibold text-lg">Many</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Loved Ones</p>
            </div>
            <div className="w-px h-12 bg-border/50"></div>
            <div className="text-center">
              <Infinity className="w-5 h-5 mx-auto mb-2 text-muted-foreground" />
              <p className="font-semibold text-lg">Forever</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">Memories</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Right side Hero Image */}
      <div className="w-full md:w-1/2 h-[50vh] md:h-auto relative overflow-hidden">
        <div className="absolute inset-0 bg-black/10 z-10"></div>
        <img 
          src="https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=2000" 
          alt="Sandeep and Prathyusha" 
          className="w-full h-full object-cover object-center"
        />
        
        {/* Floating text on image */}
        <div className="absolute right-12 bottom-24 z-20 hidden md:block">
          <p className="font-serif italic text-white/90 text-3xl rotate-[-5deg]">
            Every picture<br/>tells a story
          </p>
          <svg className="w-12 h-12 text-white/80 mt-2 ml-4 rotate-[-10deg]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </div>
      </div>
    </div>
  );
}

function HeartIcon(props: any) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
    </svg>
  );
}
