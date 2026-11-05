import React from 'react';
import { Loader2 } from 'lucide-react';

export const PageLoadingFallback: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
      <Loader2 className="w-8 h-8 animate-spin text-[#a67272]" />
      <p className="text-xs text-[#554c4c] font-medium tracking-wide">Loading...</p>
    </div>
  );
};

export default PageLoadingFallback;

