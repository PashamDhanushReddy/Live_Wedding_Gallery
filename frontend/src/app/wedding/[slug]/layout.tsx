import Link from 'next/link';

export default async function WeddingLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return (
    <div className="min-h-screen bg-neutral-950 text-white selection:bg-white/30 font-sans">
      <header className="sticky top-0 z-50 bg-neutral-950/80 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href={`/wedding/${slug}`} className="font-semibold text-lg tracking-widest uppercase">
            WEDDING
          </Link>
          <nav className="flex gap-6 text-xs tracking-widest font-medium text-neutral-400">
            <Link href={`/wedding/${slug}/your-photos`} className="hover:text-white transition-colors uppercase">
              Your Photos
            </Link>
            <Link href={`/wedding/${slug}/all-photos`} className="hover:text-white transition-colors uppercase">
              All Photos
            </Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
