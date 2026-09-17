import { ExternalLink, Heart, Code } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-4xl min-h-[calc(100vh-5rem)] flex flex-col justify-center">
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-serif text-foreground mb-4">
          About The App
        </h1>
        <div className="w-16 h-1 bg-primary mx-auto rounded-full"></div>
      </div>

      <div className="bg-card shadow-sm rounded-2xl p-8 md:p-12 mb-8 border border-border/50">
        <div className="flex items-center gap-3 mb-6">
          <Heart className="text-primary w-6 h-6" />
          <h2 className="text-2xl font-semibold">Live Wedding Gallery</h2>
        </div>
        
        <p className="text-muted-foreground leading-relaxed text-lg mb-6">
          Welcome to the Live Wedding Gallery, a seamless and interactive platform designed to let guests and loved ones share, view, and relive the magical moments of the wedding in real-time. With advanced AI facial recognition, the platform instantly categorizes photos, making it effortless to find pictures of the Bride, Groom, and everyone else celebrating the special day.
        </p>
        
        <p className="text-muted-foreground leading-relaxed text-lg">
          Our goal is to ensure that no memory goes unnoticed and that every smile captured is beautifully preserved forever.
        </p>
      </div>

      <div className="bg-secondary/30 rounded-2xl p-8 md:p-12 text-center border border-border/50">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Code className="text-primary w-8 h-8" />
        </div>
        <h3 className="text-xl font-medium mb-2">Developed By</h3>
        <p className="text-2xl font-serif text-foreground mb-6">Pasham Dhanush Reddy</p>
        
        <a 
          href="https://pashamdhanushreddy.github.io/E-Portfolio/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-foreground text-background px-6 py-3 rounded-full font-medium hover:bg-foreground/90 transition-all shadow-md"
        >
          View Portfolio
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}
