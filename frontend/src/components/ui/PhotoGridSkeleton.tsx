import React from 'react';

interface PhotoGridSkeletonProps {
  count?: number;
}

export const PhotoGridSkeleton: React.FC<PhotoGridSkeletonProps> = ({ count = 15 }) => {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <div 
      className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 md:gap-4"
      aria-label="Loading photos"
      role="status"
    >
      {items.map((i) => (
        <div 
          key={i}
          className="relative rounded-xl overflow-hidden aspect-[4/3] bg-stone-200/60 border border-stone-200/40 shadow-sm"
        >
          {/* Shimmer gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
        </div>
      ))}
    </div>
  );
};

export default PhotoGridSkeleton;
