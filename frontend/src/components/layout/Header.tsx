import { Link, useLocation } from "react-router-dom";
import { Heart, Menu, Search, Camera } from "lucide-react";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    
    window.addEventListener("scroll", handleScroll, { passive: true });
    // Check initial position in case of refresh midway
    handleScroll();
    
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "Photos", path: "/photos" },
    { name: "About", path: "/about" },
    { name: "Share", path: "/share" },
  ];

  return (
    <header 
      className={`fixed top-0 left-0 z-50 w-full transition-all duration-300 ${
        isScrolled || mobileMenuOpen
          ? "bg-white/80 backdrop-blur-md border-b border-border/50 shadow-sm py-0"
          : "bg-transparent border-b border-transparent py-1"
      }`}
    >
      <div className="container mx-auto px-4 md:px-8 h-14 md:h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex flex-col items-center">
          <div className="flex items-center gap-1 font-serif text-2xl md:text-3xl font-bold tracking-tight text-[#2d2626]">
            S <Heart className="w-4 h-4 md:w-5 md:h-5 text-[#b36c73] fill-[#b36c73]" /> P
          </div>
          <p className="text-[7px] md:text-[9px] tracking-[0.3em] text-[#554c4c] font-semibold uppercase mt-0 md:mt-0.5">
            Our Story Forever
          </p>
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
        <div className="hidden md:flex items-center gap-4">
          <Link to="/photographer" className="p-2 text-muted-foreground hover:text-foreground transition-colors" title="Photographer Portal">
            <Camera className="w-5 h-5" />
          </Link>
          <button className="p-2 text-muted-foreground hover:text-foreground transition-colors">
            <Search className="w-5 h-5" />
          </button>
          
          <div className="flex items-center gap-2 bg-secondary px-3 py-1.5 rounded-full text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            LIVE
          </div>
          
          <Link
            to="/find"
            className="bg-primary text-primary-foreground px-6 py-2.5 rounded-full text-sm font-medium hover:bg-primary/90 transition-all shadow-sm"
          >
            Find My Photos
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
                  to="/find"
                  onClick={() => setMobileMenuOpen(false)}
                  className="bg-primary text-primary-foreground px-6 py-2 rounded-full text-sm font-medium"
                >
                  Find My Photos
                </Link>
                <Link
                  to="/photographer"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-2 ml-2 text-muted-foreground hover:text-foreground"
                >
                  <Camera className="w-5 h-5" />
                </Link>
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
