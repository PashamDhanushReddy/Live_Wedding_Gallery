import Gallery from '@/components/Gallery';
import MobileUploadButton from '@/components/MobileUploadButton';

// Mock function until Django API is connected
async function getPhotos(slug: string) {
  // We'll replace this with an actual fetch to Django later
  return [];
}

export default async function AllPhotosPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const photos = await getPhotos(slug);
  
  return (
    <div className="bg-neutral-950 min-h-screen">
      <div className="max-w-[1600px] mx-auto py-8">
        <Gallery initialPhotos={photos} weddingSlug={slug} />
        <MobileUploadButton weddingSlug={slug} />
      </div>
    </div>
  );
}
