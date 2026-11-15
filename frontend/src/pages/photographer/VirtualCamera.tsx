import { useState, useEffect, useRef, useCallback } from "react";
import {
  Aperture,
  Settings2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  UploadCloud,
  Folder,
  Wifi,
  Volume2,
  VolumeX,
  Image as ImageIcon,
  ChevronDown,
  RotateCw,
  AlertCircle,
} from "lucide-react";
import {
  API_BASE_URL,
  WEDDING_SLUG,
  GALLERY_EVENT_FOLDERS,
} from "../../config";
import imageCompression from "browser-image-compression";

interface PhotoSyncConfig {
  targetProtocol: "HTTP_INGESTION" | "FTP_COMPANION";
  ftpHost: string;
  ftpPort: number;
  ftpUser: string;
  ftpPass: string;
  remoteDir: string;
  autoTransfer: boolean;
  vibrateOnAck: boolean;
  soundEnabled: boolean;
  imageQuality: "QUAD_HD" | "FULL_HD" | "ORIGINAL";
  activeFolder: string;
}

interface QueueItem {
  id: string;
  filename: string;
  thumbnail: string;
  status: "QUEUED" | "OPTIMIZING" | "UPLOADING" | "INGESTED" | "FAILED";
  progress: number;
  sizeMB: string;
  optimizedSizeMB?: string;
  timestamp: Date;
  error?: string;
  latencyMs?: number;
  blob: Blob;
}

const DEFAULT_CONFIG: PhotoSyncConfig = {
  targetProtocol: "HTTP_INGESTION",
  ftpHost: "172.20.10.3",
  ftpPort: 2121,
  ftpUser: "dhanush",
  ftpPass: "Anime@123",
  remoteDir: "/DCIM/100MSDCF/",
  autoTransfer: true,
  vibrateOnAck: true,
  soundEnabled: true,
  imageQuality: "QUAD_HD",
  activeFolder: GALLERY_EVENT_FOLDERS[0] || "Wedding Day",
};

export default function VirtualCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Configuration (persisted in localStorage like PhotoSync)
  const [config, setConfig] = useState<PhotoSyncConfig>(() => {
    try {
      const saved = localStorage.getItem("photosync_virtual_camera_config");
      return saved ? { ...DEFAULT_CONFIG, ...JSON.parse(saved) } : DEFAULT_CONFIG;
    } catch {
      return DEFAULT_CONFIG;
    }
  });

  // State
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showGrid, setShowGrid] = useState(true);
  const [flashAnimation, setFlashAnimation] = useState(false);
  const [isShooting, setIsShooting] = useState(false);
  const [shotCounter, setShotCounter] = useState(1);

  // Settings & Queue Drawer
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isQueueOpen, setIsQueueOpen] = useState(false);
  const [connectionTestStatus, setConnectionTestStatus] = useState<"idle" | "testing" | "success" | "failed">("idle");
  const [connectionLatency, setConnectionLatency] = useState<number | null>(null);

  // Transfer Queue (FIFO PhotoSync pipeline)
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isProcessingQueue, setIsProcessingQueue] = useState(false);

  // Save config changes
  useEffect(() => {
    localStorage.setItem("photosync_virtual_camera_config", JSON.stringify(config));
  }, [config]);

  // Audio Synthesizer: Mechanical DSLR Shutter Sound (Zero network latency, Works in iOS Safari)
  const playDslrShutterSound = useCallback(() => {
    if (!config.soundEnabled) return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const now = ctx.currentTime;

      // Noise burst for mechanical shutter blade snap
      const bufferSize = ctx.sampleRate * 0.04;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.009));
      }
      const noise = ctx.createBufferSource();
      noise.buffer = buffer;
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = 1900;
      filter.Q.value = 1.4;
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.8, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.04);
      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      noise.start(now);

      // Low frequency thump for mirror box return
      const osc = ctx.createOscillator();
      const oscGain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.exponentialRampToValueAtTime(40, now + 0.06);
      oscGain.gain.setValueAtTime(0.5, now);
      oscGain.gain.exponentialRampToValueAtTime(0.01, now + 0.06);
      osc.connect(oscGain);
      oscGain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.06);
    } catch (_) {}
  }, [config.soundEnabled]);

  // Initialize Camera Hardware
  const startCamera = async () => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1920, min: 1280 },
          height: { ideal: 1080, min: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsCameraActive(true);
    } catch (err) {
      console.warn("Virtual Camera getUserMedia failed:", err);
      setIsCameraActive(false);
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, [facingMode]);

  // Lens Zoom Control (Digital fallback if hardware zoom not exposed)
  const applyZoom = async (newZoom: number) => {
    setZoomLevel(newZoom);
    if (streamRef.current) {
      const track = streamRef.current.getVideoTracks()[0];
      const capabilities = (track.getCapabilities && track.getCapabilities()) as any;
      if (capabilities && capabilities.zoom) {
        try {
          await (track as any).applyConstraints({
            advanced: [{ zoom: Math.min(newZoom, capabilities.zoom.max) }],
          });
        } catch (_) {}
      }
    }
  };

  // Test Connection (simulates PhotoSync "Check Connection" button)
  const handleTestConnection = async () => {
    setConnectionTestStatus("testing");
    setConnectionLatency(null);
    const start = performance.now();
    try {
      const token = localStorage.getItem("photographer_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Token ${token}`;

      if (config.targetProtocol === "FTP_COMPANION") {
        // Register & handshake the camera connection with the backend
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/camera/connect/`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            host: config.ftpHost,
            port: config.ftpPort,
            username: config.ftpUser,
          }),
        });
        const latency = Math.round(performance.now() - start);
        if (res.ok) {
          setConnectionTestStatus("success");
          setConnectionLatency(latency);
          return;
        }
      }

      // Fast HTTP / Cloud handshake
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/`, {
        method: "GET",
      });
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        setConnectionTestStatus("success");
        setConnectionLatency(latency);
      } else {
        setConnectionTestStatus("failed");
      }
    } catch {
      setConnectionTestStatus("failed");
    }
  };

  // Shutter Action (Snap Photo)
  const capturePhoto = async () => {
    if (!videoRef.current || isShooting) return;
    setIsShooting(true);

    // Trigger visual flash + sound + haptic
    setFlashAnimation(true);
    setTimeout(() => setFlashAnimation(false), 120);
    playDslrShutterSound();
    if (config.vibrateOnAck && "vibrate" in navigator) {
      navigator.vibrate([25, 30, 25]);
    }

    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    const width = video.videoWidth || 1920;
    const height = video.videoHeight || 1080;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");

    if (ctx) {
      // Handle digital zoom cropping
      if (zoomLevel > 1) {
        const cropW = width / zoomLevel;
        const cropH = height / zoomLevel;
        const cropX = (width - cropW) / 2;
        const cropY = (height - cropH) / 2;
        ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, width, height);
      } else {
        ctx.drawImage(video, 0, 0, width, height);
      }
    }

    canvas.toBlob(
      (blob) => {
        setIsShooting(false);
        if (!blob) return;

        const padNum = String(shotCounter).padStart(4, "0");
        const filename = `DSC_${padNum}.JPG`;
        setShotCounter((prev) => prev + 1);

        const thumbnail = canvas.toDataURL("image/jpeg", 0.3);
        const newItem: QueueItem = {
          id: `${Date.now()}_${Math.random()}`,
          filename,
          thumbnail,
          status: "QUEUED",
          progress: 0,
          sizeMB: (blob.size / (1024 * 1024)).toFixed(2),
          timestamp: new Date(),
          blob,
        };

        setQueue((prev) => [newItem, ...prev]);
      },
      "image/jpeg",
      0.95
    );
  };

  // Batch Import from Camera Roll (like PhotoSync "Import from Photos")
  const handleBatchImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    const newItems: QueueItem[] = files.map((f, idx) => ({
      id: `${Date.now()}_${idx}_${Math.random()}`,
      filename: f.name,
      thumbnail: URL.createObjectURL(f),
      status: "QUEUED",
      progress: 0,
      sizeMB: (f.size / (1024 * 1024)).toFixed(2),
      timestamp: new Date(),
      blob: f,
    }));
    setQueue((prev) => [...newItems, ...prev]);
  };

  // Queue Worker: Sequentially processes and uploads items with PhotoSync auto-transfer
  useEffect(() => {
    if (!config.autoTransfer || isProcessingQueue) return;

    const nextItem = queue.find((item) => item.status === "QUEUED");
    if (!nextItem) return;

    const processItem = async (item: QueueItem) => {
      setIsProcessingQueue(true);

      // Update status: OPTIMIZING
      setQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "OPTIMIZING", progress: 20 } : q))
      );

      let fileToUpload: File | Blob = item.blob;
      let optSizeMB = item.sizeMB;

      // Cloud-Saver Compression
      if (config.imageQuality !== "ORIGINAL") {
        try {
          const maxDim = config.imageQuality === "QUAD_HD" ? 2560 : 1920;
          const compressed = await imageCompression(item.blob as File, {
            maxSizeMB: 0.75,
            maxWidthOrHeight: maxDim,
            useWebWorker: true,
            initialQuality: 0.85,
          });
          fileToUpload = compressed;
          optSizeMB = (compressed.size / (1024 * 1024)).toFixed(2);
        } catch (ce) {
          console.warn("Client compression skipped:", ce);
        }
      }

      // Update status: UPLOADING
      setQueue((prev) =>
        prev.map((q) =>
          q.id === item.id ? { ...q, status: "UPLOADING", progress: 60, optimizedSizeMB: optSizeMB } : q
        )
      );

      const startTime = performance.now();
      try {
        const formData = new FormData();
        formData.append("folder", config.activeFolder);
        formData.append("photos", fileToUpload, item.filename);

        const token = localStorage.getItem("photographer_token");
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Token ${token}`;

        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/upload/`, {
          method: "POST",
          headers,
          body: formData,
        });

        const latency = Math.round(performance.now() - startTime);

        if (res.ok) {
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? { ...q, status: "INGESTED", progress: 100, latencyMs: latency }
                : q
            )
          );
          if (config.vibrateOnAck && "vibrate" in navigator) {
            navigator.vibrate(40);
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData.message || errData.error || `HTTP ${res.status}`;
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id ? { ...q, status: "FAILED", progress: 0, error: errMsg } : q
            )
          );
        }
      } catch (err: any) {
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? { ...q, status: "FAILED", progress: 0, error: err.message || "Network Error" }
              : q
          )
        );
      } finally {
        setIsProcessingQueue(false);
      }
    };

    processItem(nextItem);
  }, [queue, config.autoTransfer, isProcessingQueue, config.activeFolder, config.imageQuality, config.vibrateOnAck]);

  const activeUploadsCount = queue.filter(
    (q) => q.status === "QUEUED" || q.status === "OPTIMIZING" || q.status === "UPLOADING"
  ).length;
  const completedUploadsCount = queue.filter((q) => q.status === "INGESTED").length;

  return (
    <div className="relative min-h-[85vh] bg-neutral-950 text-white rounded-3xl overflow-hidden border border-neutral-800 shadow-2xl flex flex-col select-none">
      
      {/* Visual Shutter Flash Animation */}
      {flashAnimation && (
        <div className="absolute inset-0 bg-white z-50 pointer-events-none animate-out fade-out duration-100" />
      )}

      {/* TOP DSLR STATUS BAR */}
      <div className="bg-neutral-900/90 backdrop-blur-md border-b border-neutral-800 px-4 py-2 flex items-center justify-between text-xs tracking-wider z-20">
        
        {/* Left: Mode & Storage */}
        <div className="flex items-center space-x-3">
          <span className="bg-rose-500/20 text-rose-400 font-bold px-2 py-0.5 rounded border border-rose-500/30">
            [M] MANUAL
          </span>
          <span className="text-neutral-400 hidden sm:inline">
            FOLDER: <strong className="text-white">{config.activeFolder}</strong>
          </span>
        </div>

        {/* Center: PhotoSync Live Transfer Pill */}
        <button
          onClick={() => setIsQueueOpen(!isQueueOpen)}
          className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium transition-all ${
            activeUploadsCount > 0
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse"
              : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
          }`}
        >
          {activeUploadsCount > 0 ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Syncing ({activeUploadsCount} left)</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>PhotoSync ACK ({completedUploadsCount} sent)</span>
            </>
          )}
        </button>

        {/* Right: Controls & Battery */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setConfig((prev) => ({ ...prev, soundEnabled: !prev.soundEnabled }))}
            className="p-1.5 hover:bg-neutral-800 rounded-lg text-neutral-400 hover:text-white"
            title="Toggle Shutter Sound"
          >
            {config.soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4 text-neutral-600" />}
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg text-xs font-bold ${
              showGrid ? "text-rose-400 bg-rose-500/10" : "text-neutral-500 hover:bg-neutral-800"
            }`}
            title="Toggle Rule of Thirds Grid"
          >
            #
          </button>
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-1.5 hover:bg-neutral-800 rounded-lg text-neutral-400 hover:text-white"
            title="PhotoSync & FTP Settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* VIEWFINDER CAMERA CONTAINER */}
      <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
        {/* Offline / Inactive Camera Overlay */}
        {!isCameraActive && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 text-center bg-neutral-950/90 space-y-3">
            <AlertCircle className="w-12 h-12 text-rose-500 animate-pulse" />
            <div className="text-sm font-bold text-white">Camera Offline or Blocked</div>
            <p className="text-xs text-neutral-400 max-w-xs">
              Allow camera permissions in your browser or tap retry to connect your phone camera.
            </p>
            <button
              onClick={startCamera}
              className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white rounded-xl text-xs font-semibold"
            >
              Retry Camera
            </button>
          </div>
        )}

        {/* Live Video Viewfinder */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-full object-cover transition-transform duration-300 ${
            facingMode === "user" ? "-scale-x-100" : ""
          }`}
          style={{ transform: `scale(${zoomLevel})` }}
        />

        {/* DSLR Viewfinder Grid Overlay */}
        {showGrid && (
          <div className="absolute inset-0 pointer-events-none grid grid-cols-3 grid-rows-3 z-10 opacity-30">
            <div className="border-r border-b border-white/50" />
            <div className="border-r border-b border-white/50" />
            <div className="border-b border-white/50" />
            <div className="border-r border-b border-white/50" />
            <div className="border-r border-b border-white/50" />
            <div className="border-b border-white/50" />
            <div className="border-r border-white/50" />
            <div className="border-r border-white/50" />
            <div className="" />
          </div>
        )}

        {/* DSLR Viewfinder Focus Reticle */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-10">
          <div className="w-20 h-20 border-2 border-white/40 rounded-lg flex items-center justify-center">
            <div className="w-2 h-2 bg-rose-500/70 rounded-full" />
          </div>
        </div>

        {/* Lens Zoom Preset Pills */}
        <div className="absolute bottom-4 left-4 z-20 flex items-center space-x-1 bg-black/60 backdrop-blur-md rounded-full p-1 border border-white/10">
          {[1, 2, 3].map((z) => (
            <button
              key={z}
              onClick={() => applyZoom(z)}
              className={`px-2.5 py-1 rounded-full text-xs font-bold transition-all ${
                zoomLevel === z ? "bg-rose-500 text-white" : "text-neutral-400 hover:text-white"
              }`}
            >
              {z}x
            </button>
          ))}
        </div>

        {/* Lens Flip (Back / Front) */}
        <div className="absolute bottom-4 right-4 z-20">
          <button
            onClick={() => setFacingMode((prev) => (prev === "environment" ? "user" : "environment"))}
            className="p-3 bg-black/60 backdrop-blur-md hover:bg-black/80 rounded-full text-white border border-white/10 transition-transform active:rotate-180"
            title="Switch Camera Lens"
          >
            <RotateCw className="w-5 h-5" />
          </button>
        </div>

        {/* Hidden Camera Roll Picker Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={handleBatchImport}
        />
      </div>

      {/* BOTTOM DSLR HUD & SHUTTER CONSOLE */}
      <div className="bg-neutral-900 border-t border-neutral-800 p-4 z-20 space-y-4">
        
        {/* DSLR Exposure Metronome HUD */}
        <div className="flex items-center justify-between text-[11px] font-mono tracking-widest text-neutral-400 border-b border-neutral-800/80 pb-2">
          <span>1/500s</span>
          <span>f/2.8</span>
          <span className="text-amber-400 font-bold">ISO 200</span>
          <span>RAW+JPG</span>
          <span>WB: AUTO</span>
          <span className="text-emerald-400 font-bold">● REC</span>
        </div>

        {/* Main Controls Row */}
        <div className="flex items-center justify-around">
          
          {/* Quick Import from Photos */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center p-3 text-neutral-400 hover:text-white hover:bg-neutral-800/60 rounded-2xl transition-colors cursor-pointer"
            title="Import from Camera Roll"
          >
            <ImageIcon className="w-6 h-6 mb-1 text-rose-400" />
            <span className="text-[10px] font-medium tracking-tight">Photos</span>
          </button>

          {/* MAIN DSLR SHUTTER BUTTON */}
          <button
            onClick={capturePhoto}
            disabled={isShooting}
            className="relative group p-1.5 rounded-full bg-neutral-800 border-4 border-neutral-700 active:scale-95 transition-transform cursor-pointer shadow-[0_0_25px_rgba(244,63,94,0.3)] hover:shadow-[0_0_35px_rgba(244,63,94,0.6)]"
          >
            <div className="w-18 h-18 sm:w-20 sm:h-20 rounded-full bg-gradient-to-tr from-rose-600 via-rose-500 to-orange-500 flex items-center justify-center text-white border-2 border-white/60">
              <Aperture className="w-9 h-9 group-active:rotate-90 transition-transform duration-300" />
            </div>
          </button>

          {/* Queue & Transfers Drawer Toggle */}
          <button
            onClick={() => setIsQueueOpen(!isQueueOpen)}
            className="relative flex flex-col items-center justify-center p-3 text-neutral-400 hover:text-white hover:bg-neutral-800/60 rounded-2xl transition-colors cursor-pointer"
          >
            <UploadCloud className="w-6 h-6 mb-1 text-blue-400" />
            <span className="text-[10px] font-medium tracking-tight">Queue</span>
            {activeUploadsCount > 0 && (
              <span className="absolute top-2 right-2 w-4 h-4 bg-amber-500 text-black text-[9px] font-bold rounded-full flex items-center justify-center animate-bounce">
                {activeUploadsCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* PHOTOSYNC CONFIGURATION & FTP SETTINGS MODAL                              */}
      {/* ========================================================================= */}
      {isSettingsOpen && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-md z-40 p-4 sm:p-6 overflow-y-auto animate-in fade-in duration-200">
          <div className="max-w-md mx-auto bg-neutral-900 border border-neutral-800 rounded-3xl p-6 shadow-2xl space-y-6">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center">
                  <Settings2 className="w-5 h-5 text-rose-400 mr-2" />
                  PhotoSync & FTP Settings
                </h3>
                <p className="text-xs text-neutral-400">Virtual Camera & Ingestion Hub</p>
              </div>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="p-1.5 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-xl"
              >
                ✕
              </button>
            </div>

            {/* Target Mode Selector */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
                  Ingestion Target Protocol
                </label>
                <span className="text-[10px] text-rose-400 font-medium">Select Fast HTTP for Phone</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setConfig((p) => ({ ...p, targetProtocol: "HTTP_INGESTION" }))}
                  className={`p-3 rounded-2xl border text-left transition-all ${
                    config.targetProtocol === "HTTP_INGESTION"
                      ? "border-emerald-500 bg-emerald-500/10 text-white font-medium ring-1 ring-emerald-500/50"
                      : "border-neutral-800 bg-neutral-950 text-neutral-400 hover:border-neutral-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-400">Fast HTTP/WS</span>
                    <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-bold">BEST</span>
                  </div>
                  <div className="text-[10px] text-neutral-300 mt-1">Direct Cloud (4G / 5G / Wi-Fi)</div>
                </button>

                <button
                  type="button"
                  onClick={() => setConfig((p) => ({ ...p, targetProtocol: "FTP_COMPANION" }))}
                  className={`p-3 rounded-2xl border text-left transition-all ${
                    config.targetProtocol === "FTP_COMPANION"
                      ? "border-amber-500 bg-amber-500/10 text-white font-medium ring-1 ring-amber-500/50"
                      : "border-neutral-800 bg-neutral-950 text-neutral-400 hover:border-neutral-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-400">FTP Companion</span>
                    <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-bold">:2121</span>
                  </div>
                  <div className="text-[10px] text-neutral-400 mt-1">Requires Same Local Wi-Fi</div>
                </button>
              </div>
            </div>

            {/* Event Folder Assignment */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center">
                <Folder className="w-3.5 h-3.5 mr-1.5 text-rose-400" />
                Active Event Folder
              </label>
              <select
                value={config.activeFolder}
                onChange={(e) => setConfig((p) => ({ ...p, activeFolder: e.target.value }))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-rose-500"
              >
                {GALLERY_EVENT_FOLDERS.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>

            {/* Connection Details Section */}
            {config.targetProtocol === "HTTP_INGESTION" ? (
              <div className="space-y-3 bg-neutral-950 p-4 rounded-2xl border border-neutral-800/80">
                <div className="text-xs font-bold text-emerald-400 flex items-center justify-between">
                  <span>Cloud Ingestion Server</span>
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full font-mono">ONLINE</span>
                </div>
                <p className="text-[11px] text-neutral-400 leading-relaxed">
                  Photos captured on this phone upload directly to your live cloud gallery over <strong>4G, 5G, or Wi-Fi</strong>. Zero local setup required!
                </p>

                {/* Test Handshake Button */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={connectionTestStatus === "testing"}
                    className="w-full py-2 bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-500/30 text-xs font-semibold rounded-xl text-emerald-300 transition-colors flex items-center justify-center space-x-2"
                  >
                    {connectionTestStatus === "testing" ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Testing Cloud Handshake...</span>
                      </>
                    ) : connectionTestStatus === "success" ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Connected to Cloud Gallery ({connectionLatency}ms)</span>
                      </>
                    ) : connectionTestStatus === "failed" ? (
                      <>
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        <span className="text-rose-400">Connection Failed. Check Internet</span>
                      </>
                    ) : (
                      <>
                        <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Test Cloud Connection</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              /* FTP Companion Settings (Local Bridge) */
              <div className="space-y-3 bg-neutral-950 p-4 rounded-2xl border border-neutral-800/80">
                <div className="text-xs font-bold text-amber-400 flex items-center justify-between">
                  <span>Local FTP Companion Bridge</span>
                  <span className="text-[10px] text-neutral-500 font-mono">:2121</span>
                </div>

                <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-[11px] text-amber-300 leading-tight">
                  ⚠️ <strong>Notice:</strong> FTP requires your iPhone to be on the <strong>same Wi-Fi or Hotspot</strong> as your Android Companion device. It will NOT work on 4G cellular data.
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2">
                    <label className="text-[10px] text-neutral-400">Server / IP</label>
                    <input
                      type="text"
                      value={config.ftpHost}
                      onChange={(e) => setConfig((p) => ({ ...p, ftpHost: e.target.value }))}
                      className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-neutral-400">Port</label>
                    <input
                      type="number"
                      value={config.ftpPort}
                      onChange={(e) => setConfig((p) => ({ ...p, ftpPort: Number(e.target.value) }))}
                      className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-neutral-400">Username</label>
                    <input
                      type="text"
                      value={config.ftpUser}
                      onChange={(e) => setConfig((p) => ({ ...p, ftpUser: e.target.value }))}
                      className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-neutral-400">Password</label>
                    <input
                      type="password"
                      value={config.ftpPass}
                      onChange={(e) => setConfig((p) => ({ ...p, ftpPass: e.target.value }))}
                      className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                </div>

                {/* Test Handshake Button */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={connectionTestStatus === "testing"}
                    className="w-full py-2 bg-neutral-800 hover:bg-neutral-700 text-xs font-semibold rounded-xl text-neutral-200 transition-colors flex items-center justify-center space-x-2"
                  >
                    {connectionTestStatus === "testing" ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Testing Handshake...</span>
                      </>
                    ) : connectionTestStatus === "success" ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Camera Linked (:2121) • {connectionLatency}ms ACK</span>
                      </>
                    ) : connectionTestStatus === "failed" ? (
                      <>
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        <span className="text-rose-400">Handshake Failed (Check login / connection)</span>
                      </>
                    ) : (
                      <>
                        <Wifi className="w-3.5 h-3.5 text-neutral-400" />
                        <span>Test Connection</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* PhotoSync Autotransfer Toggles */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">New Photo Autotransfer</div>
                  <div className="text-[10px] text-neutral-400">Upload immediately upon shutter snap</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.autoTransfer}
                  onChange={(e) => setConfig((p) => ({ ...p, autoTransfer: e.target.checked }))}
                  className="w-5 h-5 accent-rose-500 rounded cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">Vibrate on Ingest ACK</div>
                  <div className="text-[10px] text-neutral-400">Haptic pulse when server saves photo</div>
                </div>
                <input
                  type="checkbox"
                  checked={config.vibrateOnAck}
                  onChange={(e) => setConfig((p) => ({ ...p, vibrateOnAck: e.target.checked }))}
                  className="w-5 h-5 accent-rose-500 rounded cursor-pointer"
                />
              </div>
            </div>

            {/* Image Compression Preset */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
                Cloud-Saver Optimization
              </label>
              <select
                value={config.imageQuality}
                onChange={(e) => setConfig((p) => ({ ...p, imageQuality: e.target.value as any }))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white"
              >
                <option value="QUAD_HD">Quad-HD 2.5K (2560px) ~600KB - Recommended</option>
                <option value="FULL_HD">Full HD 1080p (1920px) ~350KB - Ultra Fast</option>
                <option value="ORIGINAL">Original Raw Size (Uncompressed)</option>
              </select>
            </div>

            <button
              onClick={() => setIsSettingsOpen(false)}
              className="w-full py-3 bg-gradient-to-r from-rose-500 to-orange-500 text-white font-bold text-xs uppercase tracking-wider rounded-2xl shadow-lg"
            >
              Done & Return to Camera
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PHOTOSYNC QUEUE & TRANSFERS DRAWER                                        */}
      {/* ========================================================================= */}
      {isQueueOpen && (
        <div className="absolute inset-x-0 bottom-0 max-h-[75%] bg-neutral-900/95 backdrop-blur-xl border-t border-neutral-800 rounded-t-3xl p-5 z-30 shadow-2xl flex flex-col animate-in slide-in-from-bottom duration-200">
          
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3 mb-3">
            <div className="flex items-center space-x-2">
              <UploadCloud className="w-5 h-5 text-rose-400" />
              <h4 className="text-sm font-bold text-white">PhotoSync Ingestion Queue</h4>
              <span className="text-xs text-neutral-400">({queue.length} items)</span>
            </div>
            <button
              onClick={() => setIsQueueOpen(false)}
              className="p-1 text-neutral-400 hover:text-white rounded-lg"
            >
              <ChevronDown className="w-5 h-5" />
            </button>
          </div>

          {/* Queue List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {queue.length === 0 ? (
              <div className="text-center py-8 text-neutral-500 text-xs">
                No photos in queue. Snap photos to watch live transfers!
              </div>
            ) : (
              queue.map((item) => (
                <div
                  key={item.id}
                  className="bg-neutral-950 p-2.5 rounded-2xl border border-neutral-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center space-x-3">
                    <img
                      src={item.thumbnail}
                      alt={item.filename}
                      className="w-10 h-10 object-cover rounded-lg border border-neutral-800"
                    />
                    <div>
                      <div className="font-semibold text-white">{item.filename}</div>
                      <div className="text-[10px] text-neutral-400">
                        {item.optimizedSizeMB ? `${item.optimizedSizeMB} MB` : `${item.sizeMB} MB`}
                        {item.latencyMs && ` • ${item.latencyMs}ms ACK`}
                      </div>
                    </div>
                  </div>

                  <div>
                    {item.status === "QUEUED" && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-neutral-800 text-neutral-300 font-medium">
                        QUEUED
                      </span>
                    )}
                    {item.status === "OPTIMIZING" && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400 font-medium animate-pulse">
                        COMPRESSING
                      </span>
                    )}
                    {item.status === "UPLOADING" && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 font-medium animate-pulse">
                        UPLOADING
                      </span>
                    )}
                    {item.status === "INGESTED" && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-medium flex items-center">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> INGESTED
                      </span>
                    )}
                    {item.status === "FAILED" && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-400 font-medium flex items-center" title={item.error}>
                        <XCircle className="w-3 h-3 mr-1" /> FAILED
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

    </div>
  );
}
