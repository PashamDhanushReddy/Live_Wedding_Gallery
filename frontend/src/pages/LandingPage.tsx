import { Link } from "react-router-dom";
import { Camera, Image as ImageIcon, Calendar, MapPin } from "lucide-react";
import coupleImage from "../assets/couple.png";
import bgImage from "../assets/bg_blue.png";
import mobileBg from "../assets/mobile_bg.png";

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[#faf7f5]">
      {/* Background for Desktop */}
      <div 
        className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-40 z-0 pointer-events-none hidden md:block"
        style={{ backgroundImage: `url(${bgImage})` }}
      ></div>

      {/* Background for Mobile */}
      <div 
        className="absolute inset-0 w-full h-full bg-no-repeat bg-[length:100%_100%] opacity-40 z-0 pointer-events-none block md:hidden"
        style={{ backgroundImage: `url(${mobileBg})` }}
      ></div>

      <div className="relative z-10 container mx-auto px-6 pt-12 md:pt-16 pb-16 min-h-[90vh] flex flex-col items-center justify-start text-center">
        
        {/* Top Tagline */}
        <div className="flex items-center justify-center gap-4 mb-4 md:mb-6">
          <div className="w-12 h-px bg-border/80"></div>
          <p className="text-xs md:text-sm tracking-[0.3em] uppercase text-[#554c4c] font-medium">
            Together Forever
          </p>
          <div className="w-12 h-px bg-border/80"></div>
        </div>
        
        {/* Names */}
        <div className="relative mb-4 md:mb-6">
          <h1 className="text-5xl md:text-7xl font-serif text-[#2d2626] leading-tight flex flex-col">
            <span className="mb-[-10px] md:mb-[-20px] z-10">Sandeep Reddy</span>
            <span className="italic text-4xl md:text-6xl text-[#a07171] font-serif z-0 my-2">&amp;</span>
            <span className="mt-[-10px] md:mt-[-20px] z-10">Prathyusha</span>
          </h1>

          {/* Floating side text (hidden on very small screens, visible on md+) */}
          <div className="absolute -right-8 md:-right-24 top-1/2 md:top-2/3 transform -translate-y-1/2 rotate-[-10deg] hidden sm:flex flex-col items-center">
            <p className="font-script text-2xl md:text-3xl text-[#a07171] leading-none">Two<br/>Hearts<br/>One Story</p>
            <HeartIcon className="w-5 h-5 text-[#a07171] mt-1" />
          </div>
        </div>
        
        {/* Cursive Tagline */}
        <div className="flex flex-col items-center mb-6 md:mb-10">
          <p className="font-script text-3xl md:text-4xl text-[#2d2626] mb-2 md:mb-3">
            A beautiful journey<br/>begins...
          </p>
          <HeartIcon className="w-6 h-6 text-[#a07171]" />
        </div>
        
        {/* Date & Location */}
        <div className="flex flex-col items-center gap-2 md:gap-3 text-sm md:text-base text-[#554c4c] mb-4 md:mb-6">
          <div className="flex items-center gap-3">
            <Calendar className="w-4 h-4 md:w-5 md:h-5 text-[#a07171]" />
            <span className="font-medium">November 21, 2026</span>
          </div>
          <div className="flex items-center gap-3">
            <MapPin className="w-4 h-4 md:w-5 md:h-5 text-[#a07171]" />
            <span className="font-medium">Hyderabad, Telangana</span>
          </div>
        </div>
        
        <div className="w-12 h-px bg-[#a07171]/40 mb-4 md:mb-6"></div>
        
        {/* Paragraph */}
        <p className="text-[#554c4c] font-serif text-sm md:text-lg max-w-md mx-auto leading-relaxed mb-6 md:mb-10">
          A celebration of love, family and beautiful moments. <br/>
          Join us in reliving the memories of our special day.
        </p>
        
        {/* Buttons (Standard pills instead of big boxes) */}
        <div className="flex flex-col sm:flex-row gap-4 mb-12 md:mb-20 z-20">
          <Link 
            to="/photos" 
            className="flex items-center justify-center gap-2 bg-[#a07171] text-white px-8 py-3.5 rounded-full font-medium hover:bg-[#8a5f5f] transition-all shadow-md"
          >
            <Camera className="w-5 h-5" />
            View All Photos
          </Link>
          <Link 
            to="/find" 
            className="flex items-center justify-center gap-2 bg-white/60 backdrop-blur-sm border border-[#a07171]/30 text-[#554c4c] px-8 py-3.5 rounded-full font-medium hover:bg-white/80 transition-all shadow-sm"
          >
            <ImageIcon className="w-5 h-5" />
            Find My Photos
          </Link>
        </div>
        
        {/* Bottom Text */}
        <div className="flex items-center justify-center gap-4 mt-auto z-20">
          <div className="w-12 md:w-20 h-px bg-border/80"></div>
          <div className="flex items-center gap-2">
            <p className="font-script text-2xl md:text-3xl text-[#a07171]">
              Thank you for being a part of our story
            </p>
            <HeartIcon className="w-5 h-5 text-[#a07171]" />
          </div>
          <div className="w-12 md:w-20 h-px bg-border/80"></div>
        </div>

      </div>

    </div>
  );
}

function HeartIcon(props: any) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
    </svg>
  );
}
