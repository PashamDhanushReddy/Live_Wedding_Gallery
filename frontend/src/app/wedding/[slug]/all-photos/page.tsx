import Gallery from '@/components/Gallery';
import MobileUploadButton from '@/components/MobileUploadButton';
import { Search, Download } from 'lucide-react';
import Header from '@/components/Header';

async function getPhotos(slug: string) {
  return [];
}

export default async function AllPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const photos = await getPhotos(slug);
  
  return (
    <div className="bg-[var(--color-background)] min-h-screen flex flex-col pt-20">
      <Header weddingSlug={slug} />

      <div className="w-full max-w-6xl mx-auto px-4 py-8 flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
          <div className="text-center sm:text-left">
            <h1 className="font-serif text-3xl mb-2">All Wedding Photos</h1>
            <p className="text-neutral-500 text-sm">Explore all the beautiful moments</p>
          </div>
          <button className="hidden sm:flex bg-neutral-900 text-white px-5 py-2.5 rounded-full text-sm font-medium items-center justify-center gap-2 hover:bg-neutral-800 transition-colors">
            <Download className="w-4 h-4" />
            Download All
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative w-full max-w-2xl mx-auto mb-6">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-neutral-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-12 pr-4 py-3.5 bg-neutral-100 border border-neutral-200 rounded-full text-sm placeholder-neutral-400 focus:border-neutral-300 focus:bg-white focus:ring-0 transition-colors shadow-sm"
            placeholder="Search photos..."
          />
        </div>

        {/* Category Filters */}
        <div className="flex items-center justify-center flex-wrap gap-2 md:gap-4 mb-10">
          <button className="px-5 py-2 rounded-full text-sm font-medium bg-[var(--color-brand)] text-white shadow-md shadow-brand/20">All</button>
          <button className="px-5 py-2 rounded-full text-sm font-medium bg-neutral-100 text-neutral-600 hover:bg-neutral-200 transition-colors border border-neutral-200">Ceremony</button>
          <button className="px-5 py-2 rounded-full text-sm font-medium bg-neutral-100 text-neutral-600 hover:bg-neutral-200 transition-colors border border-neutral-200">Reception</button>
          <button className="px-5 py-2 rounded-full text-sm font-medium bg-neutral-100 text-neutral-600 hover:bg-neutral-200 transition-colors border border-neutral-200">Family</button>
          <button className="px-5 py-2 rounded-full text-sm font-medium bg-neutral-100 text-neutral-600 hover:bg-neutral-200 transition-colors border border-neutral-200">Friends</button>
        </div>

        {/* Gallery */}
        <div className="w-full pb-8">
          <Gallery initialPhotos={photos} weddingSlug={slug} />
        </div>
      </div>
      
      <MobileUploadButton weddingSlug={slug} />
    </div>
  );
}
