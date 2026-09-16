import { useEffect, useState } from "react";
import { Camera, Image as ImageIcon, AlertTriangle, HardDrive, Wifi, Server, CheckCircle2 } from "lucide-react";
import { API_BASE_URL, WEDDING_SLUG } from "../../config";

export default function PhotographerDashboard() {
  const [stats, setStats] = useState({
    total_photos: 0,
    processing: 0,
    failed: 0,
    connection_status: 'STOPPED',
    local_ip: 'Not connected',
    storage_mb: 0.0,
    queue_waiting: 0
  });

  useEffect(() => {
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
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const storageGB = (stats.storage_mb / 1024).toFixed(2);
  const storageLimit = 3.0;
  const storagePercentage = (stats.storage_mb / (storageLimit * 1024)) * 100;
  
  const isStorageWarning = storagePercentage > 80;
  const isStorageCritical = storagePercentage > 95;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white uppercase tracking-wider">Photographer Dashboard</h1>
        <p className="text-neutral-400 mt-2">Live Wedding: SandeepReddy & Prathyusha</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Connection Status Panel */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 lg:col-span-1 space-y-6">
          <h2 className="text-lg font-semibold text-white border-b border-neutral-800 pb-3">System Status</h2>
          
          <div className="flex justify-between items-center">
            <div className="flex items-center text-neutral-400"><Server className="w-4 h-4 mr-2"/> FTP SERVER</div>
            <div className={`px-3 py-1 rounded-full text-xs font-bold ${stats.connection_status === 'RUNNING' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-neutral-800 text-neutral-500'}`}>
              ● {stats.connection_status}
            </div>
          </div>

          <div className="flex justify-between items-center">
            <div className="flex items-center text-neutral-400"><Wifi className="w-4 h-4 mr-2"/> FTP ADDRESS</div>
            <div className="font-mono text-white bg-black px-2 py-1 rounded text-sm tracking-wider">
              {stats.local_ip === 'Not connected' ? '-' : `${stats.local_ip}:2121`}
            </div>
          </div>

          <div className="flex justify-between items-center">
            <div className="flex items-center text-neutral-400"><Camera className="w-4 h-4 mr-2"/> CAMERA</div>
            <div className={`text-sm font-medium ${stats.connection_status === 'RUNNING' ? 'text-emerald-500' : 'text-neutral-500'}`}>
              {stats.connection_status === 'RUNNING' ? 'Ready to receive' : 'Offline'}
            </div>
          </div>
          
          <div className="space-y-2 pt-2">
             <div className="flex justify-between items-center">
                <div className="flex items-center text-neutral-400"><HardDrive className="w-4 h-4 mr-2"/> TEMP STORAGE</div>
                <div className={`text-sm font-medium ${isStorageCritical ? 'text-rose-500' : isStorageWarning ? 'text-yellow-500' : 'text-white'}`}>
                  {storageGB} GB / {storageLimit} GB
                </div>
             </div>
             <div className="w-full bg-neutral-950 rounded-full h-2 mt-2">
                <div 
                  className={`h-2 rounded-full ${isStorageCritical ? 'bg-rose-500' : isStorageWarning ? 'bg-yellow-500' : 'bg-emerald-500'}`} 
                  style={{ width: `${Math.min(storagePercentage, 100)}%` }}
                ></div>
             </div>
          </div>
        </div>

        {/* Transfer Stats Panel */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-white border-b border-neutral-800 pb-3 mb-6">Upload Statistics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
             <div className="bg-black/50 rounded-xl p-4 border border-neutral-800/50 text-center">
                <div className="text-neutral-400 text-sm mb-1">PHOTOS RECEIVED</div>
                <div className="text-2xl font-bold text-white">{stats.total_photos + stats.queue_waiting}</div>
             </div>
             
             <div className="bg-emerald-950/20 rounded-xl p-4 border border-emerald-900/30 text-center">
                <div className="text-emerald-500/70 text-sm mb-1">UPLOADED</div>
                <div className="text-2xl font-bold text-emerald-400">{stats.total_photos}</div>
             </div>
             
             <div className="bg-blue-950/20 rounded-xl p-4 border border-blue-900/30 text-center">
                <div className="text-blue-500/70 text-sm mb-1">WAITING IN QUEUE</div>
                <div className="text-2xl font-bold text-blue-400">{stats.queue_waiting}</div>
             </div>
             
             <div className="bg-rose-950/20 rounded-xl p-4 border border-rose-900/30 text-center">
                <div className="text-rose-500/70 text-sm mb-1">FAILED</div>
                <div className="text-2xl font-bold text-rose-400">{stats.failed}</div>
             </div>
          </div>
        </div>
      </div>
      
      {/* Sony Camera Setup Guide */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
        <div className="bg-neutral-800/50 px-6 py-4 border-b border-neutral-800">
          <h2 className="text-lg font-semibold text-white">Configure Sony Camera FTP</h2>
        </div>
        <div className="p-6">
          <ol className="space-y-4 text-neutral-300 list-decimal list-inside marker:text-neutral-500 marker:font-mono">
            <li>Connect your Sony camera to the same Wi-Fi network as the Android Companion App.</li>
            <li>On the Android App, tap <strong>Start FTP</strong>. Note the FTP Address shown above.</li>
            <li>On your Sony Camera, go to <strong>Menu ➔ Network ➔ FTP Transfer ➔ FTP Server Settings</strong>.</li>
            <li>Enter the <span className="text-emerald-400 font-mono">FTP IP</span> and Port (<span className="text-emerald-400 font-mono">2121</span>) displayed above.</li>
            <li>Enter Username: <span className="text-emerald-400 font-mono bg-black px-1 rounded">wedding</span> and Password: <span className="text-emerald-400 font-mono bg-black px-1 rounded">password123</span> (or as shown on the app).</li>
            <li>Enable <strong>Auto FTP Transfer</strong> on the camera.</li>
            <li className="text-white font-medium flex items-start mt-4 pt-4 border-t border-neutral-800">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 mr-2 flex-shrink-0 mt-0.5" />
              <span>Shoot normally! The camera will keep the original photo safely on your SD card and send a copy to the Android phone, which automatically queues and uploads to this live gallery.</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
}
