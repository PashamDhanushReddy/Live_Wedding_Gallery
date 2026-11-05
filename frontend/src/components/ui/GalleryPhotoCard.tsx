import React, { useState, memo, useMemo } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface GalleryPhotoItem {
  id: number;
  url: string;
  secure_url?: string;
  thumbnail_url?: string;
  preview_url?: string;
  large_preview_url?: string;
  download_url?: string;
  aspect?: string;
  category?: string;
  width?: number;
  height?: number;
}

interface GalleryPhotoCardProps {
  photo: GalleryPhotoItem;
  index: number;
  onClick: (index: number) => void;
}

/**
 * Builds responsive Cloudinary srcset & sizes for modern devices.
 * Automatically injects f_auto,q_auto and proportional width breakpoints.
 */
function getResponsiveSrcSet(baseUrl?: string): { src: string; srcSet?: string; sizes?: string } {
  if (!baseUrl) return { src: "" };

  if (baseUrl.includes('res.cloudinary.com') && baseUrl.includes('/image/upload/')) {
    const buildWidthVariant = (w: number) => {
      return baseUrl.replace(/\/image\/upload\/[^/]+\//, `/image/upload/c_limit,f_auto,q_auto,w_${w}/`) + ` ${w}w`;
    };

    const srcSet = `${buildWidthVariant(250)}, ${buildWidthVariant(400)}, ${buildWidthVariant(600)}, ${buildWidthVariant(800)}`;
    const sizes = "(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 20vw";

    return {
      src: baseUrl,
      srcSet,
      sizes,
    };
  }

  return { src: baseUrl };
}

export const GalleryPhotoCard: React.FC<GalleryPhotoCardProps> = memo(({ photo, index, onClick }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Cloudinary thumbnail URL (w_400) for grid rendering
  const thumbnailSrc = photo.thumbnail_url || photo.preview_url || photo.url;
  const imgProps = useMemo(() => getResponsiveSrcSet(thumbnailSrc), [thumbnailSrc]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(index);
    }
  };

  const handleRetry = (e: React.MouseEvent) => {
    e.stopPropagation();
    setHasError(false);
    setIsLoaded(false);
    setRetryCount(prev => prev + 1);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`View ${photo.category || 'wedding'} photo ${photo.id}`}
      onClick={() => onClick(index)}
      onKeyDown={handleKeyDown}
      className="cursor-pointer group relative rounded-xl overflow-hidden shadow-sm aspect-[4/3] bg-stone-100 border border-stone-200/40 focus:outline-none focus:ring-2 focus:ring-[#a67272] focus:ring-offset-2 transition-shadow"
    >
      {/* Skeleton Shimmer while loading */}
      {!isLoaded && !hasError && (
        <div className="absolute inset-0 bg-stone-200/70 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
        </div>
      )}

      {/* Error state */}
      {hasError ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-3 text-center bg-stone-100 text-stone-500">
          <AlertCircle className="w-5 h-5 text-stone-400 mb-1" />
          <span className="text-[11px] text-stone-500 mb-2">Image failed to load</span>
          <button
            type="button"
            onClick={handleRetry}
            className="flex items-center gap-1 text-[10px] font-semibold text-[#a67272] bg-white border border-stone-200 px-2 py-0.5 rounded-full shadow-xs hover:bg-stone-50 cursor-pointer"
          >
            <RefreshCw className="w-2.5 h-2.5" /> Retry
          </button>
        </div>
      ) : (
        <img
          key={`${photo.id}-${retryCount}`}
          src={imgProps.src}
          srcSet={imgProps.srcSet}
          sizes={imgProps.sizes}
          alt={photo.category ? `${photo.category} photo` : 'Wedding photo'}
          loading="lazy"
          decoding="async"
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
          className={`w-full h-full object-cover object-center group-hover:scale-105 transition-all duration-500 ${
            isLoaded ? 'opacity-100 scale-100' : 'opacity-0 scale-98'
          }`}
        />
      )}

      {/* Hover Scrim Overlay */}
      <div 
        aria-hidden="true"
        className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity duration-300 flex items-center justify-center pointer-events-none"
      >
        <p className="text-white font-medium text-xs md:text-sm tracking-wide">View Photo</p>
      </div>
    </div>
  );
}, (prev, next) => {
  return prev.photo.id === next.photo.id &&
         prev.photo.thumbnail_url === next.photo.thumbnail_url &&
         prev.index === next.index;
});

GalleryPhotoCard.displayName = 'GalleryPhotoCard';
export default GalleryPhotoCard;
