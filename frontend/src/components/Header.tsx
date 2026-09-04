'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import NavigationDrawer from './NavigationDrawer';

interface HeaderProps {
  weddingSlug: string;
  transparent?: boolean;
}

export default function Header({ weddingSlug, transparent = false }: HeaderProps) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (transparent) {
      const handleScroll = () => {
        setScrolled(window.scrollY > 20);
      };
      window.addEventListener('scroll', handleScroll);
      return () => window.removeEventListener('scroll', handleScroll);
    }
  }, [transparent]);

  const isDark = transparent && !scrolled;

  return (
    <header className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${isDark ? 'bg-transparent text-white' : 'bg-white/95 backdrop-blur text-black border-b border-neutral-100 shadow-sm'}`}>
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        {/* Logo */}
        <Link href={`/wedding/${weddingSlug}`} className="font-serif text-2xl tracking-widest">
          A & R
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8 font-medium text-sm">
          <Link href={`/wedding/${weddingSlug}`} className="hover:opacity-70 transition-opacity">Home</Link>
          <Link href={`/wedding/${weddingSlug}/all-photos`} className="hover:opacity-70 transition-opacity">Gallery</Link>
          <Link href="#" className="hover:opacity-70 transition-opacity">About</Link>
          <Link href="#" className="hover:opacity-70 transition-opacity">Contact</Link>
        </nav>

        {/* Desktop Login Button */}
        <div className="hidden md:block">
          <button className={`px-6 py-2 rounded-full font-medium text-sm transition-colors ${isDark ? 'bg-white text-black hover:bg-neutral-200' : 'bg-[var(--color-brand)] text-white hover:bg-[var(--color-brand-dark)]'}`}>
            Login
          </button>
        </div>

        {/* Mobile Navigation (Hamburger) */}
        <div className="md:hidden">
          <NavigationDrawer weddingSlug={weddingSlug} />
        </div>
      </div>
    </header>
  );
}
