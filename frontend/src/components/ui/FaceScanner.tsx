import React, { useState, useEffect, useRef } from "react";
import { Camera, RefreshCw, Upload, Lock, ShieldCheck, AlertCircle, Sparkles } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";
import type { GalleryPhotoItem } from "./GalleryPhotoCard";

interface FaceScannerProps {
  onPhotosFound: (photos: GalleryPhotoItem[], selfieDataUrl: string, totalMatches: number) => void;
  onClose?: () => void;
  isOverlay?: boolean;
}

const mapSearchPhoto = (p: any): GalleryPhotoItem => ({
  id: p.id,
  url: p.large_preview_url || p.preview_url || p.secure_url || p.cloudinary_url || "",
  secure_url: p.secure_url,
  thumbnail_url: p.thumbnail_url || p.preview_url || p.secure_url,
  preview_url: p.preview_url,
  large_preview_url: p.large_preview_url,
  download_url: p.download_url || p.secure_url || p.cloudinary_url,
  aspect: p.width && p.height ? `aspect-[${p.width}/${p.height}]` : "aspect-[4/3]",
  category: p.folder || "Uncategorized",
  width: p.width,
  height: p.height,
});

export default function FaceScanner({ onPhotosFound, isOverlay = false }: FaceScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const autoScanTimerRef = useRef<any>(null);

  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isStartingCamera, setIsStartingCamera] = useState(true);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("Initializing secure face scanner...");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<"idle" | "scanning" | "processing" | "no_match" | "no_face" | "error">("idle");
  const [capturedThumbnail, setCapturedThumbnail] = useState<string | null>(null);

  const stopCamera = () => {
    if (autoScanTimerRef.current) {
      clearInterval(autoScanTimerRef.current);
      autoScanTimerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  const startCamera = async () => {
    stopCamera();
    setCameraError(null);
    setIsStartingCamera(true);
    setScanStatus("scanning");
    setStatusMessage("Requesting camera access...");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera not supported on this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 640 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraActive(true);
      setIsStartingCamera(false);
      setStatusMessage("Align your face in the oval frame...");

      // Start a smooth 2-second countdown for hands-free auto-scan
      let timeLeft = 2;
      setCountdown(timeLeft);
      autoScanTimerRef.current = setInterval(() => {
        timeLeft -= 1;
        if (timeLeft > 0) {
          setCountdown(timeLeft);
        } else {
          clearInterval(autoScanTimerRef.current);
          autoScanTimerRef.current = null;
          setCountdown(null);
          handleTriggerScan();
        }
      }, 1000);
    } catch (err: any) {
      console.warn("Camera access failed:", err);
      setIsStartingCamera(false);
      setIsCameraActive(false);
      setCameraError(
        err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
          ? "Camera permission was denied. You can allow camera in browser settings or upload a selfie below."
          : "Could not open camera on this device. Please upload a selfie to access your photos."
      );
      setScanStatus("error");
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const captureFrameBlob = (): Promise<{ blob: Blob; dataUrl: string } | null> => {
    return new Promise((resolve) => {
      if (!videoRef.current) return resolve(null);
      const video = videoRef.current;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 640;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(null);

      // Mirror horizontally so snapshot matches mirrored front camera
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
      canvas.toBlob(
        (blob) => {
          if (blob) resolve({ blob, dataUrl });
          else resolve(null);
        },
        "image/jpeg",
        0.92
      );
    });
  };

  const processSelfie = async (fileOrBlob: Blob, previewUrl: string) => {
    setIsProcessing(true);
    setScanStatus("processing");
    setStatusMessage("Searching wedding photos with facial AI...");
    setCapturedThumbnail(previewUrl);
    stopCamera();

    const formData = new FormData();
    formData.append("file", fileOrBlob, "guest_selfie.jpg");

    try {
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/search/`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        if (data.code === "NO_FACE" || data.status === "no_face_detected") {
          setScanStatus("no_face");
          setStatusMessage("No face was detected. Please ensure good lighting and face the camera directly.");
        } else {
          setScanStatus("error");
          setStatusMessage(data.message || data.error || "Failed to search photos. Please retry.");
        }
        return;
      }

      const rawPhotos = data.photos || [];
      const mappedPhotos = rawPhotos.map(mapSearchPhoto);

      if (mappedPhotos.length === 0) {
        setScanStatus("no_match");
        setStatusMessage("Face verified! We couldn't find any photos of you yet. The photographer is actively shooting—new photos will appear soon.");
      } else {
        // Success: pass to parent
        onPhotosFound(mappedPhotos, previewUrl, data.matches_count || mappedPhotos.length);
      }
    } catch (err: any) {
      console.error("Face search failed:", err);
      setScanStatus("error");
      setStatusMessage("Network error during face search. Please check your connection and retry.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTriggerScan = async () => {
    if (autoScanTimerRef.current) {
      clearInterval(autoScanTimerRef.current);
      autoScanTimerRef.current = null;
      setCountdown(null);
    }
    const captured = await captureFrameBlob();
    if (!captured) {
      setScanStatus("error");
      setStatusMessage("Could not capture camera frame. Please retry.");
      return;
    }
    await processSelfie(captured.blob, captured.dataUrl);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const previewUrl = URL.createObjectURL(file);
      processSelfie(file, previewUrl);
    }
  };

  return (
    <div className={`w-full max-w-lg mx-auto ${isOverlay ? "p-4" : "p-6"}`}>
      <div className="bg-white/90 backdrop-blur-xl border border-[#f0e4dc] rounded-3xl shadow-xl overflow-hidden p-6 sm:p-8 text-center transition-all duration-300">
        
        {/* Privacy Shield Banner */}
        <div className="flex items-center justify-center gap-2 mb-4 bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-xs font-semibold py-1.5 px-4 rounded-full w-fit mx-auto">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Privacy Protection Enabled</span>
        </div>

        <h2 className="font-serif text-2xl sm:text-3xl text-[#2d2626] font-medium mb-2">
          Find Your Photos
        </h2>
        <p className="text-xs sm:text-sm text-[#736363] max-w-sm mx-auto mb-6 leading-relaxed">
          To protect everyone's privacy, our live gallery only displays photos featuring you. Look into the camera to unlock your memories.
        </p>

        {/* Camera / Viewfinder Box */}
        <div className="relative w-64 h-64 sm:w-72 sm:h-72 mx-auto rounded-3xl overflow-hidden bg-neutral-900 border-2 border-[#a67272]/30 shadow-inner flex items-center justify-center mb-6">
          
          {isCameraActive && (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover -scale-x-100"
              />

              {/* Biometric Oval Mask Overlay */}
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div className="w-44 h-56 border-2 border-dashed border-white/60 rounded-[50%] shadow-[0_0_15px_rgba(255,255,255,0.3)] animate-pulse" />
              </div>

              {/* Scanning Laser Line */}
              <div className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#b36c73] to-transparent shadow-[0_0_12px_#b36c73] animate-[scan_2.5s_ease-in-out_infinite]" />

              {/* Countdown overlay */}
              {countdown !== null && (
                <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px] flex flex-col items-center justify-center text-white">
                  <span className="text-5xl font-bold font-serif drop-shadow-md animate-scale">
                    {countdown}
                  </span>
                  <p className="text-xs tracking-wider uppercase font-medium mt-2 text-white/90">
                    Scanning Face...
                  </p>
                </div>
              )}
            </>
          )}

          {/* Fallback / Processing / Error view inside viewfinder */}
          {!isCameraActive && (
            <div className="flex flex-col items-center justify-center p-6 text-center text-white/80">
              {isStartingCamera ? (
                <>
                  <RefreshCw className="w-10 h-10 animate-spin text-[#b36c73] mb-3" />
                  <p className="text-xs font-medium text-white/90">Starting camera...</p>
                </>
              ) : isProcessing ? (
                <>
                  <Sparkles className="w-12 h-12 text-[#b36c73] animate-bounce mb-3" />
                  <p className="text-xs font-medium text-white">Analyzing facial biometrics...</p>
                  <p className="text-[11px] text-white/60 mt-1">Searching gallery photos</p>
                </>
              ) : capturedThumbnail ? (
                <div className="relative w-full h-full">
                  <img
                    src={capturedThumbnail}
                    alt="Captured Face"
                    className="w-full h-full object-cover rounded-2xl"
                  />
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                    <p className="text-xs text-white px-2 py-1 bg-black/60 rounded-md">Scanned Face</p>
                  </div>
                </div>
              ) : (
                <>
                  <Camera className="w-12 h-12 text-white/40 mb-3" />
                  <p className="text-xs font-medium text-white/80">Camera Inactive</p>
                </>
              )}
            </div>
          )}
        </div>

        {/* Live Status Description */}
        <p className="text-xs sm:text-sm font-medium text-[#554c4c] mb-6 min-h-[2.5rem] flex items-center justify-center gap-2 px-4">
          {scanStatus === "processing" ? (
            <RefreshCw className="w-4 h-4 animate-spin text-[#a67272]" />
          ) : scanStatus === "no_face" || scanStatus === "error" ? (
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          ) : scanStatus === "no_match" ? (
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
          ) : (
            <Lock className="w-3.5 h-3.5 text-[#a67272]" />
          )}
          <span>{statusMessage}</span>
        </p>

        {/* Actions / Buttons */}
        <div className="flex flex-col gap-3">
          {isCameraActive && (
            <button
              type="button"
              onClick={handleTriggerScan}
              disabled={isProcessing}
              className="w-full bg-[#a67272] text-white py-3.5 rounded-full font-medium text-sm hover:bg-[#8f5e5e] transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
            >
              <Camera className="w-4 h-4" />
              Scan My Face Now
            </button>
          )}

          {(!isCameraActive || cameraError || scanStatus === "no_face" || scanStatus === "no_match") && (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                type="button"
                onClick={startCamera}
                disabled={isProcessing}
                className="flex-1 bg-[#a67272] text-white py-3 rounded-full font-medium text-xs sm:text-sm hover:bg-[#8f5e5e] transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
              >
                <RefreshCw className="w-4 h-4" />
                Retry Camera Scan
              </button>
              
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="flex-1 bg-white border border-[#f0e4dc] text-[#554c4c] py-3 rounded-full font-medium text-xs sm:text-sm hover:bg-[#fcf5f1] transition-all shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
              >
                <Upload className="w-4 h-4 text-[#a67272]" />
                Upload Selfie Instead
              </button>
            </div>
          )}

          {/* Hidden File Input for fallback upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="user"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

      </div>
    </div>
  );
}
