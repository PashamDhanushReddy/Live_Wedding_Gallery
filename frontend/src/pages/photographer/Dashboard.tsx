import { useEffect, useState } from "react";
import { Camera, Image as ImageIcon, AlertTriangle, CheckCircle2 } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";

export default function PhotographerDashboard() {
  const [stats, setStats] = useState({
    total_photos: 0,
    processing: 0,
    failed: 0,
    connection_status: 'DISCONNECTED'
  });

  useEffect(() => {
    // Fetch stats
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/stats/`);
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (e) {
        console.error("Failed to fetch stats", e);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Dashboard</h1>
        <p className="text-neutral-400 mt-2">SandeepReddy ❤️ Prathyusha</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-neutral-400 font-medium">Camera</h3>
            <Camera className="w-5 h-5 text-neutral-500" />
          </div>
          <div className="mt-4 flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${stats.connection_status === 'CONNECTED' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <p className="text-2xl font-semibold text-white">{stats.connection_status}</p>
          </div>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-neutral-400 font-medium">Total Photos</h3>
            <ImageIcon className="w-5 h-5 text-neutral-500" />
          </div>
          <p className="mt-4 text-3xl font-semibold text-white">{stats.total_photos}</p>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-neutral-400 font-medium">Processing</h3>
            <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="mt-4 text-3xl font-semibold text-white">{stats.processing}</p>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-neutral-400 font-medium">Failed</h3>
            <AlertTriangle className="w-5 h-5 text-rose-500" />
          </div>
          <p className="mt-4 text-3xl font-semibold text-white">{stats.failed}</p>
        </div>
      </div>
      
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <h3 className="text-xl font-semibold text-white mb-4">Quick Setup</h3>
          <p className="text-neutral-400 mb-4">Connect your Sony camera to the mobile hotspot, then navigate to the Camera tab to get your FTP credentials.</p>
      </div>
    </div>
  );
}
