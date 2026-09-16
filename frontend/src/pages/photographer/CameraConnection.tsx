import { useState } from "react";
import { Server, Wifi } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";

export default function CameraConnection() {
  const [loading, setLoading] = useState(false);
  const [connectionData, setConnectionData] = useState({
    host: "ftp.live-wedding-gallery.onrender.com",
    port: 2121,
    username: "camera_sandeep-prathyusha",
    password: "password123", // In real app, generate securely
    remote_directory: "/DCIM/",
    status: "DISCONNECTED"
  });

  const connectCamera = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/camera/connect/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: connectionData.host,
          port: connectionData.port,
          username: connectionData.username
        })
      });
      if (res.ok) {
        setConnectionData(prev => ({ ...prev, status: "CONNECTED" }));
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const disconnectCamera = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/camera/disconnect/`, {
        method: 'POST'
      });
      if (res.ok) {
        setConnectionData(prev => ({ ...prev, status: "DISCONNECTED" }));
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Camera Setup</h1>
        <p className="text-neutral-400 mt-2">Enter these details into your Sony Camera's FTP settings.</p>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
        <div className="p-6 space-y-6">
          <div className="flex items-center space-x-3 text-emerald-400 bg-emerald-500/10 p-4 rounded-xl">
            <Wifi className="w-5 h-5" />
            <span className="font-medium text-sm">Make sure your camera is connected to a Mobile Hotspot.</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-400">FTP Host (IP/Domain)</label>
              <input type="text" readOnly value={connectionData.host} className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-rose-500" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-400">Port</label>
              <input type="text" readOnly value={connectionData.port} className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-rose-500" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-400">Username</label>
              <input type="text" readOnly value={connectionData.username} className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-rose-500" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-400">Password</label>
              <input type="text" readOnly value={connectionData.password} className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-rose-500" />
            </div>
            <div className="space-y-2 md:col-span-2">
              <label className="text-sm font-medium text-neutral-400">Remote Directory</label>
              <input type="text" readOnly value={connectionData.remote_directory} className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-rose-500" />
            </div>
          </div>
        </div>

        <div className="bg-neutral-950 p-6 border-t border-neutral-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Server className="w-5 h-5 text-neutral-500" />
            <span className="text-neutral-400">
              Status: <strong className={connectionData.status === 'CONNECTED' ? 'text-emerald-400' : 'text-neutral-200'}>{connectionData.status}</strong>
            </span>
          </div>
          <div className="space-x-3 flex">
            {connectionData.status === 'DISCONNECTED' ? (
               <button onClick={connectCamera} disabled={loading} className="px-6 py-2.5 bg-gradient-to-r from-rose-500 to-orange-500 hover:from-rose-400 hover:to-orange-400 text-white font-medium rounded-xl transition-all shadow-[0_0_20px_rgba(244,63,94,0.3)] disabled:opacity-50">
                 Provision Account
               </button>
            ) : (
               <button onClick={disconnectCamera} disabled={loading} className="px-6 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-white font-medium rounded-xl transition-all disabled:opacity-50">
                 Disconnect
               </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
