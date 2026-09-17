import { useState, useEffect } from "react";
import QRCode from "react-qr-code";
import { Share2, MessageCircle, Copy, Check, Smartphone } from "lucide-react";

export default function SharePage() {
  const [url, setUrl] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setUrl(window.location.origin);
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const shareText = "Check out our Live Wedding Gallery! 📸✨";

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Live Wedding Gallery",
          text: shareText,
          url: url,
        });
      } catch (err) {
        console.error("Share failed", err);
      }
    } else {
      handleCopy();
    }
  };

  return (
    <div className="container mx-auto px-4 py-16 max-w-3xl min-h-[calc(100vh-5rem)] flex flex-col justify-center">
      <div className="text-center mb-10">
        <h1 className="text-4xl md:text-5xl font-serif text-foreground mb-4">
          Share The Joy
        </h1>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">
          Invite friends and family to view the live gallery and relive the beautiful moments with us.
        </p>
      </div>

      <div className="bg-card shadow-sm rounded-3xl p-8 md:p-12 border border-border/50 flex flex-col items-center">
        
        {/* QR Code Section */}
        <div className="bg-white p-6 rounded-2xl shadow-sm mb-8 inline-block">
          {url && (
            <QRCode 
              value={url} 
              size={200}
              level="H"
              fgColor="#1a1a1a"
            />
          )}
        </div>
        
        <p className="text-sm text-muted-foreground uppercase tracking-widest font-semibold mb-8">
          Scan to view gallery
        </p>

        {/* Link Copy Box */}
        <div className="w-full max-w-md flex items-center bg-secondary/50 border border-border rounded-xl p-2 mb-8">
          <input 
            type="text" 
            readOnly 
            value={url} 
            className="flex-1 bg-transparent border-none outline-none text-foreground text-sm px-3 truncate"
          />
          <button 
            onClick={handleCopy}
            className="flex items-center gap-2 bg-background border border-border text-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-secondary transition-colors"
          >
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>

        {/* Share Buttons */}
        <div className="flex flex-wrap justify-center gap-4 w-full max-w-md">
          <a
            href={`https://wa.me/?text=${encodeURIComponent(shareText + " " + url)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 bg-[#25D366] text-white px-4 py-3 rounded-xl font-medium hover:bg-[#20bd5a] transition-colors"
          >
            <MessageCircle className="w-5 h-5" />
            WhatsApp
          </a>
          
          <button
            onClick={handleNativeShare}
            className="flex-1 flex items-center justify-center gap-2 bg-primary text-primary-foreground px-4 py-3 rounded-xl font-medium hover:bg-primary/90 transition-colors"
          >
            <Share2 className="w-5 h-5" />
            More Options
          </button>
        </div>
      </div>
    </div>
  );
}
