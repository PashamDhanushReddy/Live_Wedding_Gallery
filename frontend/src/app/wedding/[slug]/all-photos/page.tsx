import Gallery from '@/components/Gallery';
import MobileUploadButton from '@/components/MobileUploadButton';
import Link from 'next/link';
import { ChevronLeft, Search } from 'lucide-react';

// Mock function until Django API is connected
async function getPhotos(slug: string) {
  // We'll replace this with an actual fetch to Django later
  return [];
}

export default async function AllPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const photos = await getPhotos(slug);
  
  return (
    <div className="bg-[var(--color-background)] min-h-screen flex flex-col">
      
      {/* Top Bar */}
      <div className="flex items-center p-6 sticky top-0 z-10 bg-[var(--color-background)]/95 backdrop-blur">
        <Link href={`/wedding/${slug}`} className="p-2 -ml-2 text-neutral-500 hover:bg-neutral-100 rounded-full transition-colors">
          <ChevronLeft className="w-6 h-6" />
        </Link>
        <h1 className="flex-1 text-center font-serif text-xl mr-8">All Wedding Photos</h1>
      </div>

      <div className="w-full max-w-5xl mx-auto px-4 flex flex-col">
        <div className="text-center mb-6">
          <p className="text-neutral-500 text-sm">Explore all the beautiful moments</p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full max-w-md mx-auto mb-8">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-neutral-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-11 pr-4 py-3 bg-neutral-100 border-transparent rounded-full text-sm placeholder-neutral-400 focus:border-neutral-300 focus:bg-white focus:ring-0 transition-colors"
            placeholder="Search photos..."
          />
        </div>

        {/* Gallery */}
        <div className="w-full pb-8">
          <Gallery initialPhotos={photos} weddingSlug={slug} />
        </div>
      </div>
      
      {/* Keep the mobile upload button for testing as requested previously */}
      <MobileUploadButton weddingSlug={slug} />
    </div>
  );
}
