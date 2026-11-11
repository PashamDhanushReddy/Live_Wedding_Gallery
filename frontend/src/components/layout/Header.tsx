import { Link, useLocation } from "react-router-dom";
import { Heart, Menu, Camera } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import weddingLogo from "../../assets/wedding-logo.png";

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "My Photos", path: "/photos" },
    { name: "About", path: "/about" },
    { name: "Share", path: "/share" },
  ];

  return (
    <header className="fixed top-0 left-0 z-50 w-full bg-white/20 backdrop-blur-md border-b border-white/20 shadow-sm transition-all duration-300">
      <div className="container mx-auto px-4 md:px-8 h-14 md:h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <img
            src={weddingLogo}
            alt="Sandeep & Prathyusha"
            className="w-9 h-9 md:w-11 md:h-11 object-contain drop-shadow-sm group-hover:scale-105 transition-transform duration-200"
          />
          <div className="flex flex-col">
            <div className="flex items-center gap-1 font-serif text-xl md:text-2xl font-bold tracking-tight text-[#2d2626] leading-none">
              S <Heart className="w-3.5 h-3.5 md:w-4 md:h-4 text-[#b36c73] fill-[#b36c73]" /> P
            </div>
            <p className="text-[7px] md:text-[8px] tracking-[0.25em] text-[#554c4c] font-semibold uppercase mt-0.5">
              Our Story Forever
            </p>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              to={link.path}
              className={`text-sm font-medium transition-colors hover:text-primary ${
                location.pathname === link.path ? "text-primary border-b-2 border-primary py-1" : "text-muted-foreground"
              }`}
            >
              {link.name}
            </Link>
          ))}
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Link 
            to="/photographer/login" 
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-600 bg-white/60 hover:bg-white/90 border border-stone-200/80 rounded-full transition-all shadow-xs" 
            title="Photographer Portal (Full Gallery)"
          >
            <Camera className="w-3.5 h-3.5 text-[#a07171]" />
            <span>Photographer</span>
          </Link>
          
          <div className="flex items-center gap-2 bg-secondary px-3 py-1.5 rounded-full text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            LIVE
          </div>
          
          <Link
            to="/photos"
            className="bg-primary text-primary-foreground px-5 py-2 rounded-full text-xs sm:text-sm font-medium hover:bg-primary/90 transition-all shadow-sm"
          >
            Scan Face
          </Link>
        </div>

        {/* Mobile Menu Toggle */}
        <button
          className="md:hidden p-2 text-foreground"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {/* Mobile Nav */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-border bg-background"
          >
            <nav className="flex flex-col p-4">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`py-3 text-sm font-medium border-b border-border/50 ${
                    location.pathname === link.path ? "text-primary" : "text-foreground"
                  }`}
                >
                  {link.name}
                </Link>
              ))}
              <div className="flex items-center justify-between py-4">
                <div className="flex items-center gap-2 bg-secondary px-3 py-1.5 rounded-full text-xs font-medium">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                  </span>
                  LIVE
                </div>
                <Link
                  to="/photos"
                  onClick={() => setMobileMenuOpen(false)}
                  className="bg-primary text-primary-foreground px-5 py-2 rounded-full text-xs font-medium"
                >
                  Scan Face
                </Link>
                <Link
                  to="/photographer/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-stone-600 bg-stone-100 rounded-full"
                >
                  <Camera className="w-4 h-4 text-[#a07171]" />
                  <span>Photographer</span>
                </Link>
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
