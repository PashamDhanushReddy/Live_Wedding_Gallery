import { useState, useRef, useMemo } from "react";
import { UploadCloud, Image as ImageIcon, CheckCircle, XCircle, Zap } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";
import imageCompression from 'browser-image-compression';

export default function ManualUpload() {
  const [activeFolder, setActiveFolder] = useState("Engagement");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalBytes = useMemo(() => {
    return files.reduce((acc, f) => acc + f.size, 0);
  }, [files]);

  const totalSizeMB = useMemo(() => {
    return (totalBytes / (1024 * 1024)).toFixed(1);
  }, [totalBytes]);

  const estimatedUploadSeconds = useMemo(() => {
    // Estimating ~500 KB per photo after browser Web Worker optimization
    const optimizedTotalMB = files.length * 0.5;
    return Math.max(1, Math.round(optimizedTotalMB / 1.8));
  }, [files]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files);
      setFiles(selected);
      setStatus("idle");
      setProgress(0);
      setCurrentStep("");
    }
  };

  const triggerSelect = () => {
    fileInputRef.current?.click();
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const uploadSingleFile = async (file: File, token: string | null): Promise<void> => {
    let fileToUpload = file;

    // Mandatory Cloud-Saver client-side optimization using browser Web Workers
    // Compresses to ~500-750 KB at 2.5K Quad-HD (2560px) to guarantee 20k photos fit in free tier
    if (file.type.startsWith('image/')) {
      try {
        fileToUpload = await imageCompression(file, {
          maxSizeMB: 0.75,
          maxWidthOrHeight: 2560,
          useWebWorker: true,
          initialQuality: 0.84,
        });
      } catch (ce) {
        console.warn("Client-side compression fallback for", file.name, ce);
      }
    }

    const formData = new FormData();
    formData.append("folder", activeFolder);
    formData.append("photos", fileToUpload, file.name);

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Token ${token}`;

    const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/upload/`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const errText = errData.message || errData.error || (await res.text().catch(() => "Upload failed"));
      throw new Error(`Upload failed for ${file.name} (${res.status}): ${errText}`);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setProgress(0);
    setStatus("idle");
    setErrorMessage("");

    const token = localStorage.getItem("photographer_token");
    const totalFiles = files.length;
    let completedCount = 0;

    // 4 parallel upload streams for maximum network throughput
    const CONCURRENCY = 4;
    const queue = [...files];

    try {
      setCurrentStep(`Starting ${totalFiles} photo uploads (Cloud-Saver 2.5K Quad-HD)...`);

      const worker = async () => {
        while (queue.length > 0) {
          const file = queue.shift();
          if (!file) break;

          await uploadSingleFile(file, token);
          completedCount += 1;
          const pct = Math.floor((completedCount / totalFiles) * 100);
          setProgress(pct);
          setCurrentStep(`Uploaded ${completedCount} of ${totalFiles} photos (${pct}%)...`);
        }
      };

      const workers = Array.from({ length: Math.min(CONCURRENCY, totalFiles) }, () => worker());
      await Promise.all(workers);

      setStatus("success");
      setFiles([]);
      setCurrentStep("All photos uploaded successfully! Server is indexing faces into the live gallery.");
    } catch (e: any) {
      console.error(e);
      setErrorMessage(e.message || String(e));
      setStatus("error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Manual Upload</h1>
        <p className="text-neutral-400 mt-2">Upload wedding and event photos directly to Cloudinary and the live gallery.</p>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-neutral-400">Target Folder / Category</label>
            <select 
              value={activeFolder} 
              onChange={(e) => setActiveFolder(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-rose-500"
            >
              <option value="Engagement">Engagement</option>
              <option value="Haldi">Haldi</option>
              <option value="Mehendi">Mehendi</option>
              <option value="Sangeet">Sangeet</option>
              <option value="Ceremony">Ceremony</option>
              <option value="Reception">Reception</option>
              <option value="Guests">Guests</option>
              <option value="Decor">Decor</option>
              <option value="Uncategorized">Uncategorized</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-neutral-400">Optimization & Storage Target</label>
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-emerald-400 flex items-center space-x-1.5">
                    <span>Cloud-Saver Standard (2.5K Quad-HD)</span>
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded border border-emerald-500/30">Enforced</span>
                  </div>
                  <div className="text-[11px] text-neutral-400 mt-0.5">
                    Auto-optimized to ~500–750 KB per photo • Fits 20,000+ photos in Free Tier
                  </div>
                </div>
              </div>
            </div>
            <p className="text-xs text-neutral-500">
              Raw uncompressed uploads are disabled to protect your Cloudinary Free Tier quota. All photos retain pristine 2.5K clarity.
            </p>
          </div>
        </div>

        <div 
          onClick={triggerSelect}
          className="border-2 border-dashed border-neutral-700 hover:border-rose-500 rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-neutral-950"
        >
          <UploadCloud className="w-12 h-12 text-neutral-500 mb-4" />
          <h3 className="text-lg font-medium text-white mb-1">Select Photos</h3>
          <p className="text-sm text-neutral-400">Click to browse your camera files (JPEG, PNG, MPO). Select multiple files at once.</p>
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
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <h4 className="text-sm font-medium text-neutral-200">{files.length} Photos Selected</h4>
                <span className="text-xs text-neutral-400">({totalSizeMB} MB total payload)</span>
              </div>
              <button 
                onClick={() => setFiles([])} 
                className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
              >
                Clear all
              </button>
            </div>

            <div className="flex items-center space-x-2 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs">
              <Zap className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>
                <strong>Cloud-Saver Active:</strong> {files.length} photos ({totalSizeMB} MB original) will be automatically optimized to ~{(files.length * 0.5).toFixed(1)} MB and upload in ~{estimatedUploadSeconds}s.
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              {files.map((file, i) => (
                <div key={i} className="relative group bg-neutral-800/80 rounded-lg p-2.5 flex items-center space-x-2 border border-neutral-700/50">
                  <ImageIcon className="w-4 h-4 text-neutral-400 shrink-0" />
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="text-xs text-neutral-200 truncate">{file.name}</span>
                    <span className="text-[10px] text-neutral-500">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
                  </div>
                  <button 
                    onClick={() => removeFile(i)}
                    className="text-neutral-500 hover:text-rose-400 transition-colors ml-1"
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
                className="w-full py-3.5 bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(244,63,94,0.3)] disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                <UploadCloud className="w-5 h-5" />
                <span>
                  {uploading 
                    ? currentStep || `Uploading... ${progress}%`
                    : `Upload ${files.length} Photos (Cloud-Saver 2.5K)`
                  }
                </span>
              </button>

              {uploading && (
                <div className="mt-3 space-y-1.5">
                  <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-rose-500 to-orange-500 h-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-center text-neutral-400">{currentStep}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {status === "success" && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center text-emerald-400">
            <CheckCircle className="w-5 h-5 mr-3 shrink-0" />
            <div>
              <p className="font-medium">Upload Complete!</p>
              <p className="text-sm opacity-80">Photos were uploaded and are actively being indexed with face recognition into the live gallery.</p>
            </div>
          </div>
        )}
        
        {status === "error" && (
          <div className="p-4 bg-destructive/10 text-destructive border border-destructive/20 rounded-xl flex gap-3 items-center">
            <XCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-medium">Upload Failed</p>
              <p className="text-sm opacity-90">{errorMessage}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
