import Link from 'next/link';
import { Camera, Image as ImageIcon } from 'lucide-react';
import Header from '@/components/Header';

export default async function WeddingLandingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <div className="min-h-screen relative flex flex-col justify-between text-white overflow-hidden">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1519741497674-611481863552?q=80&w=2070&auto=format&fit=crop')" }}
      />
      <div className="absolute inset-0 z-0 bg-black/50 backdrop-blur-[2px]" />

      {/* Global Responsive Header */}
      <Header weddingSlug={slug} transparent={true} />

      {/* Content */}
      <div className="w-full max-w-7xl mx-auto px-6 z-10 flex-1 flex flex-col justify-center mt-20">
        <div className="w-full max-w-xl text-center md:text-left space-y-12">
          <div className="space-y-4">
            <p className="font-serif text-2xl text-white/90 italic">Welcome to</p>
            <h1 className="text-5xl md:text-7xl font-serif font-medium tracking-wide">Our Wedding</h1>
            <div className="pt-2 md:pt-4 flex justify-center md:justify-start items-center gap-4">
              <div className="h-px w-12 bg-white/40 hidden md:block" />
              <span className="text-white/80 font-medium tracking-widest text-sm uppercase">24th January 2026</span>
            </div>
            <p className="text-white/80 font-light tracking-wide text-sm md:text-base mt-6 leading-relaxed max-w-md mx-auto md:mx-0">
              Relive the moments. Find yourself. Be a part of our story.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-center justify-center md:justify-start w-full max-w-md mx-auto md:mx-0">
            <Link 
              href={`/wedding/${slug}/your-photos`}
              className="w-full sm:w-auto flex-1 glass-panel-dark rounded-full py-4 px-6 flex items-center justify-center transition-transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="text-sm font-medium text-white tracking-wide">Find Your Photos</span>
            </Link>

            <Link 
              href={`/wedding/${slug}/all-photos`}
              className="w-full sm:w-auto flex-1 glass-panel rounded-full py-4 px-6 flex items-center justify-center transition-transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="text-sm font-medium text-white tracking-wide">View All Photos</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="w-full z-10 py-10 text-center md:text-left max-w-7xl mx-auto px-6">
        <p className="font-serif italic text-white/70 text-base">
          Good photos. Great memories. Together forever.
        </p>
      </div>
    </div>
  );
}
