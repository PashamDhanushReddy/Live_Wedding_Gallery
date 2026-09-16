import { useState, useRef } from "react";
import { UploadCloud, Image as ImageIcon, CheckCircle, XCircle } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";

import imageCompression from 'browser-image-compression';

export default function ManualUpload() {
  const [activeFolder, setActiveFolder] = useState("Engagement");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [compressing, setCompressing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setStatus("idle");
      setProgress(0);
    }
  };

  const triggerSelect = () => {
    fileInputRef.current?.click();
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setCompressing(true);
    setProgress(0);
    setStatus("idle");
    setErrorMessage("");

    try {
      const compressionOptions = {
        maxSizeMB: 1, 
        maxWidthOrHeight: 1920,
        // useWebWorker removed to prevent browser OOM on massive batch
      };

      const CHUNK_SIZE = 1; // 1 file at a time for maximum safety
      let processed = 0;

      for (let i = 0; i < files.length; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        const formData = new FormData();
        formData.append("folder", activeFolder);
        
        // Compress chunk
        for (const file of chunk) {
          if (file.type.startsWith('image/')) {
            try {
              const compressedFile = await imageCompression(file, compressionOptions);
              formData.append("photos", compressedFile, file.name);
            } catch (ce) {
              console.warn("Compression failed for", file.name, ce);
              formData.append("photos", file); // fallback to original if compression fails
            }
          } else {
            formData.append("photos", file);
          }
        }
        
        setCompressing(false); // After first chunk compression starts uploading

        // Upload chunk
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/upload/`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Server returned ${res.status}: ${errText}`);
        }
        
        processed += chunk.length;
        setProgress(Math.floor((processed / files.length) * 100));
      }

      setStatus("success");
      setFiles([]);
    } catch (e: any) {
      console.error(e);
      setErrorMessage(e.message || String(e));
      setStatus("error");
    } finally {
      setUploading(false);
      setCompressing(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Manual Upload</h1>
        <p className="text-neutral-400 mt-2">Upload pre-existing photos (like engagement shoots) directly from your device.</p>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden p-6 space-y-6">
        <div className="space-y-2">
          <label className="text-sm font-medium text-neutral-400">Target Folder / Category</label>
          <select 
            value={activeFolder} 
            onChange={(e) => setActiveFolder(e.target.value)}
            className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-rose-500"
          >
            <option value="Uncategorized">Uncategorized</option>
            <option value="Engagement">Engagement</option>
            <option value="Haldi">Haldi</option>
            <option value="Mehendi">Mehendi</option>
            <option value="Wedding Day">Wedding Day</option>
            <option value="Reception">Reception</option>
          </select>
        </div>

        <div 
          onClick={triggerSelect}
          className="border-2 border-dashed border-neutral-700 hover:border-rose-500 rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-neutral-950"
        >
          <UploadCloud className="w-12 h-12 text-neutral-500 mb-4" />
          <h3 className="text-lg font-medium text-white mb-1">Select Photos</h3>
          <p className="text-sm text-neutral-400">Click to browse your files (JPEG, PNG). Select multiple files at once.</p>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden" 
            multiple 
            accept="image/*"
          />
        </div>

        {files.length > 0 && (
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-neutral-300">{files.length} Photos Selected</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              {files.map((file, i) => (
                <div key={i} className="relative group bg-neutral-800 rounded-lg p-2 flex items-center space-x-2">
                  <ImageIcon className="w-4 h-4 text-neutral-400 shrink-0" />
                  <span className="text-xs text-neutral-300 truncate">{file.name}</span>
                  <button 
                    onClick={() => removeFile(i)}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-neutral-800">
              <button 
                onClick={handleUpload}
                disabled={uploading}
                className="w-full py-3 bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(244,63,94,0.3)] disabled:opacity-50"
              >
                {uploading ? (compressing ? `Compressing Images... ${progress}%` : `Uploading to Server... ${progress}%`) : "Compress & Upload to Cloud"}
              </button>
            </div>
          </div>
        )}

        {status === "success" && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center text-emerald-400">
            <CheckCircle className="w-5 h-5 mr-3" />
            <div>
              <p className="font-medium">Upload Complete!</p>
              <p className="text-sm opacity-80">Photos are being processed and pushed to the live gallery.</p>
            </div>
          </div>
        )}
        
        {status === "error" && (
          <div className="mt-4 p-4 bg-destructive/10 text-destructive rounded-xl flex gap-3 items-center">
            <XCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-medium">Upload Failed</p>
              <p className="text-sm">Please check your network and try again. Error: {errorMessage}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
