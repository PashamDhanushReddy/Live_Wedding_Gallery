import Link from 'next/link';
import { Camera, Image as ImageIcon } from 'lucide-react';

export default async function WeddingLandingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <div className="min-h-screen bg-neutral-950 text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-12 text-center">
        <div className="space-y-4">
          <h1 className="text-4xl font-light tracking-widest uppercase">Wedding</h1>
          <p className="text-neutral-400 font-medium tracking-widest text-sm uppercase">Live Photo Gallery</p>
        </div>

        <div className="space-y-4 flex flex-col items-center">
          <Link 
            href={`/wedding/${slug}/your-photos`}
            className="w-full relative group overflow-hidden rounded-2xl bg-neutral-900 border border-white/10 p-8 transition-all hover:border-white/30 hover:bg-neutral-800"
          >
            <div className="flex flex-col items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
                <Camera className="w-8 h-8 text-white/80" />
              </div>
              <div>
                <h2 className="text-xl font-medium tracking-wider">YOUR PHOTOS</h2>
                <p className="text-sm text-neutral-500 mt-2">Find photos of yourself using a quick selfie.</p>
              </div>
            </div>
          </Link>

          <Link 
            href={`/wedding/${slug}/all-photos`}
            className="w-full relative group overflow-hidden rounded-2xl bg-neutral-900 border border-white/10 p-8 transition-all hover:border-white/30 hover:bg-neutral-800"
          >
            <div className="flex flex-col items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
                <ImageIcon className="w-8 h-8 text-white/80" />
              </div>
              <div>
                <h2 className="text-xl font-medium tracking-wider">ALL PHOTOS</h2>
                <p className="text-sm text-neutral-500 mt-2">View the complete live photo feed.</p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
