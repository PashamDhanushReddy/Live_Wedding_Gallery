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
            <WhatsAppIcon />
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

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51a12.8 12.8 0 0 0-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/>
    </svg>
  );
}
