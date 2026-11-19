import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, ShieldCheck, CheckCircle2, X, AlertCircle, RefreshCw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import weddingLogo from "../../assets/wedding-logo.png";

export const CAMERA_PERMISSION_KEY = "wedding_camera_permission_requested";
export const CAMERA_PERMISSION_GRANTED_KEY = "wedding_camera_permission_granted";
export const CAMERA_PERMISSION_EVENT = "wedding_camera_permission_granted";
export const CAMERA_PERMISSION_OPEN_EVENT = "wedding_open_camera_permission";

export default function CameraPermissionModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "requesting" | "granted" | "denied" | "unsupported">("idle");
  const [message, setMessage] = useState<string>("");
  const closeTimerRef = useRef<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Only open when explicitly requested (e.g. user clicks [Scan Face & View My Photos])
    // and ONLY if this is their first time
    const handleOpen = () => {
      try {
        const alreadyPrompted = localStorage.getItem(CAMERA_PERMISSION_KEY) === "true";
        if (alreadyPrompted) {
          const wasGranted = localStorage.getItem(CAMERA_PERMISSION_GRANTED_KEY) === "true";
          navigate(wasGranted ? "/photos?autoScan=true" : "/photos");
          return;
        }
      } catch (_) {}

      setIsOpen(true);
      setStatus("idle");
      setMessage("");
    };

    window.addEventListener(CAMERA_PERMISSION_OPEN_EVENT, handleOpen);
    return () => {
      window.removeEventListener(CAMERA_PERMISSION_OPEN_EVENT, handleOpen);
      if (closeTimerRef.current) {
        clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  const requestPermission = async (isAuto = false) => {
    if (typeof navigator === "undefined" || typeof navigator.mediaDevices?.getUserMedia !== "function") {
      if (!isAuto) {
        setStatus("unsupported");
        setMessage("Camera access is not supported on this browser. You can still upload a selfie.");
        try {
          localStorage.setItem(CAMERA_PERMISSION_KEY, "true");
        } catch (_) {}
        closeTimerRef.current = setTimeout(() => {
          setIsOpen(false);
          navigate("/photos");
        }, 2200);
      }
      return;
    }

    setStatus("requesting");
    if (!isAuto) {
      setMessage("Please choose 'Allow' on your browser prompt...");
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "user" } },
        audio: false,
      });

      // Permission granted! Immediately release camera hardware
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (_) {}
      });

      setStatus("granted");
      setMessage("Camera permission granted! Opening face scanner...");
      try {
        localStorage.setItem(CAMERA_PERMISSION_KEY, "true");
        localStorage.setItem(CAMERA_PERMISSION_GRANTED_KEY, "true");
      } catch (_) {}

      // Notify any active components that camera permission was granted
      window.dispatchEvent(new CustomEvent(CAMERA_PERMISSION_EVENT));

      closeTimerRef.current = setTimeout(() => {
        setIsOpen(false);
        navigate("/photos?autoScan=true");
      }, 1200);
    } catch (err: any) {
      if (isAuto) {
        setStatus("idle");
      } else {
        setStatus("denied");
        setMessage(
          err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
            ? "Camera permission was denied. You can still upload a selfie anytime to find your photos."
            : "Could not access camera. You can still upload a selfie anytime."
        );
        try {
          localStorage.setItem(CAMERA_PERMISSION_KEY, "true");
        } catch (_) {}

        closeTimerRef.current = setTimeout(() => {
          setIsOpen(false);
          navigate("/photos");
        }, 2500);
      }
    }
  };

  const handleDismiss = () => {
    try {
      localStorage.setItem(CAMERA_PERMISSION_KEY, "true");
    } catch (_) {}
    setIsOpen(false);
  };

  const handleContinueWithoutCamera = () => {
    try {
      localStorage.setItem(CAMERA_PERMISSION_KEY, "true");
    } catch (_) {}
    setIsOpen(false);
    navigate("/photos");
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleDismiss}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Modal Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="relative w-full max-w-md bg-white/95 backdrop-blur-xl border border-[#f0e4dc] rounded-3xl shadow-2xl p-6 sm:p-8 text-center z-10 overflow-hidden"
          role="dialog"
          aria-modal="true"
        >
          {/* Close button */}
          <button
            onClick={handleDismiss}
            aria-label="Close"
            className="absolute top-4 right-4 p-2 text-stone-400 hover:text-stone-600 rounded-full hover:bg-stone-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Wedding Emblem Logo */}
          <div className="flex justify-center mb-3">
            <img
              src={weddingLogo}
              alt="Sandeep & Prathyusha"
              className="w-20 h-20 sm:w-24 sm:h-24 object-contain drop-shadow-sm"
            />
          </div>

          {/* Tagline */}
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="h-px w-6 bg-[#d9a78b]"></span>
            <span className="text-[10px] sm:text-xs font-serif uppercase tracking-[0.25em] text-[#a07171]">
              Sandeep & Prathyusha
            </span>
            <span className="h-px w-6 bg-[#d9a78b]"></span>
          </div>

          <h3 className="font-serif text-2xl sm:text-3xl text-[#2d2626] font-medium mb-2">
            Camera Permission
          </h3>

          <p className="text-xs sm:text-sm text-[#736363] leading-relaxed mb-5">
            To automatically locate and personalize photos of you using our private face recognition, please grant camera access.
          </p>

          {/* Privacy Protection Callout */}
          <div className="flex items-start gap-2.5 bg-emerald-50/90 border border-emerald-200/70 text-emerald-900 text-xs text-left p-3 rounded-2xl mb-6">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div className="leading-tight">
              <span className="font-semibold block mb-0.5">Your Privacy Is Guaranteed</span>
              <span className="text-[11px] text-emerald-700">
                Camera access is only used for an instant face scan to find your photos, and turns off immediately.
              </span>
            </div>
          </div>

          {/* Status feedback message */}
          {status === "granted" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-center gap-2 p-3 bg-emerald-100/80 text-emerald-800 text-xs sm:text-sm font-medium rounded-2xl mb-4"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{message}</span>
            </motion.div>
          )}

          {status === "denied" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-center gap-2 p-3 bg-rose-50 text-rose-700 text-xs sm:text-sm font-medium rounded-2xl mb-4"
            >
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{message}</span>
            </motion.div>
          )}

          {status === "unsupported" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-center gap-2 p-3 bg-amber-50 text-amber-800 text-xs sm:text-sm font-medium rounded-2xl mb-4"
            >
              <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
              <span>{message}</span>
            </motion.div>
          )}

          {status === "requesting" && (
            <div className="flex items-center justify-center gap-2 p-3 bg-stone-100 text-stone-700 text-xs sm:text-sm font-medium rounded-2xl mb-4">
              <RefreshCw className="w-4 h-4 animate-spin text-[#a07171]" />
              <span>{message || "Requesting camera access..."}</span>
            </div>
          )}

          {/* Action buttons */}
          {status !== "granted" && (
            <div className="flex flex-col gap-2.5">
              <button
                type="button"
                onClick={() => requestPermission(false)}
                disabled={status === "requesting"}
                className="w-full bg-[#a07171] hover:bg-[#8a5f5f] text-white py-3.5 px-6 rounded-full font-medium text-sm transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
              >
                <Camera className="w-4 h-4" />
                Allow Camera Access
              </button>

              <button
                type="button"
                onClick={handleContinueWithoutCamera}
                className="w-full py-2.5 px-4 text-stone-500 hover:text-stone-700 text-xs font-medium transition-colors cursor-pointer"
              >
                Continue Without Camera
              </button>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
