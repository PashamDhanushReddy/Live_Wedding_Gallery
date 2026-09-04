import Link from 'next/link';
import { Camera, Image as ImageIcon } from 'lucide-react';
import NavigationDrawer from '@/components/NavigationDrawer';

export default async function WeddingLandingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <div className="min-h-screen relative flex flex-col items-center justify-between text-white">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1519741497674-611481863552?q=80&w=2070&auto=format&fit=crop')" }}
      />
      <div className="absolute inset-0 z-0 bg-black/40 backdrop-blur-[2px]" />

      {/* Top Bar */}
      <div className="w-full z-10 flex justify-between items-center p-6 max-w-md mx-auto">
        <span className="font-serif text-xl tracking-widest text-white/90">A & R</span>
        <NavigationDrawer weddingSlug={slug} />
      </div>

      {/* Content */}
      <div className="w-full max-w-md px-6 z-10 flex flex-col items-center text-center space-y-12">
        <div className="space-y-4">
          <p className="font-serif text-2xl text-white/80 italic">Welcome to</p>
          <h1 className="text-5xl font-serif font-medium tracking-wide">Our Wedding</h1>
          <div className="pt-4 flex justify-center">
            <span className="text-white/60 text-sm">♥</span>
          </div>
          <p className="text-white/80 font-light tracking-wide text-sm mt-4">
            Relive the moments. Find yourself.<br/>
            Be a part of our story.
          </p>
        </div>

        <div className="w-full space-y-4">
          <Link 
            href={`/wedding/${slug}/your-photos`}
            className="w-full glass-panel-dark rounded-[24px] p-5 flex items-center gap-4 transition-transform hover:scale-[1.02] active:scale-[0.98]"
          >
            <div className="h-12 w-12 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
              <Camera className="w-6 h-6 text-white" />
            </div>
            <div className="text-left">
              <h2 className="text-base font-medium text-white tracking-wide">Find Your Photos</h2>
              <p className="text-xs text-white/70 mt-1">Take a selfie and see only your photos</p>
            </div>
          </Link>

          <Link 
            href={`/wedding/${slug}/all-photos`}
            className="w-full bg-white rounded-[24px] p-5 flex items-center gap-4 transition-transform hover:scale-[1.02] active:scale-[0.98] shadow-xl"
          >
            <div className="h-12 w-12 rounded-xl bg-neutral-100 flex items-center justify-center border border-neutral-200">
              <ImageIcon className="w-6 h-6 text-neutral-600" />
            </div>
            <div className="text-left">
              <h2 className="text-base font-medium text-neutral-900 tracking-wide">View All Photos</h2>
              <p className="text-xs text-neutral-500 mt-1">Explore the full wedding gallery</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="w-full z-10 py-10 text-center">
        <p className="font-serif italic text-white/80 text-lg">
          Good photos. Great memories.<br/>Together forever.
        </p>
        <div className="mt-4 flex items-center justify-center gap-4">
          <div className="h-px w-12 bg-white/30" />
          <span className="text-white/50 text-xs">♡</span>
          <div className="h-px w-12 bg-white/30" />
        </div>
      </div>
    </div>
  );
}
