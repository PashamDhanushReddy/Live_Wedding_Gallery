'use client';

import { useState } from 'react';
import { Menu, X, Home, Camera, Image as ImageIcon, Info, HelpCircle } from 'lucide-react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';

export default function NavigationDrawer({ weddingSlug }: { weddingSlug: string }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className="p-2 z-40 relative text-current hover:opacity-70 transition-opacity"
      >
        <Menu className="w-6 h-6" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/40 z-50 backdrop-blur-sm"
            />
            
            {/* Drawer */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 bottom-0 w-80 bg-[var(--color-background)] z-50 shadow-2xl flex flex-col"
            >
              <div className="flex items-center justify-between p-6 border-b border-black/5">
                <span className="font-serif text-xl tracking-widest text-neutral-800">A & R</span>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-neutral-100 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-neutral-500" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto py-6 flex flex-col gap-2 px-4">
                <DrawerLink 
                  href={`/wedding/${weddingSlug}`} 
                  icon={<Home className="w-5 h-5" />} 
                  label="Home" 
                  onClick={() => setIsOpen(false)} 
                />
                <DrawerLink 
                  href={`/wedding/${weddingSlug}/your-photos`} 
                  icon={<Camera className="w-5 h-5" />} 
                  label="Find Your Photos" 
                  onClick={() => setIsOpen(false)} 
                />
                <DrawerLink 
                  href={`/wedding/${weddingSlug}/all-photos`} 
                  icon={<ImageIcon className="w-5 h-5" />} 
                  label="All Photos" 
                  onClick={() => setIsOpen(false)} 
                />
                <DrawerLink 
                  href="#" 
                  icon={<Info className="w-5 h-5" />} 
                  label="About" 
                  onClick={() => setIsOpen(false)} 
                />
                <DrawerLink 
                  href="#" 
                  icon={<HelpCircle className="w-5 h-5" />} 
                  label="Help / FAQ" 
                  onClick={() => setIsOpen(false)} 
                />
              </div>

              <div className="p-8 text-center border-t border-black/5">
                <div className="flex justify-center mb-3 opacity-50">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22c4.97-4.97 8-9.69 8-14.5a8 8 0 0 0-16 0C4 12.31 7.03 17.03 12 22Z" />
                    <path d="M12 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
                  </svg>
                </div>
                <p className="text-xs text-neutral-500 mb-2">Thank you for being here with us</p>
                <span className="text-neutral-300">♥</span>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function DrawerLink({ href, icon, label, onClick }: { href: string, icon: React.ReactNode, label: string, onClick: () => void }) {
  return (
    <Link 
      href={href}
      onClick={onClick}
      className="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-neutral-100 transition-colors text-neutral-700 hover:text-neutral-900"
    >
      <span className="text-neutral-400">{icon}</span>
      <span className="font-medium text-sm">{label}</span>
    </Link>
  );
}
