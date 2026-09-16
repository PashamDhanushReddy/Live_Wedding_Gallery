import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Clock, Image as ImageIcon } from "lucide-react";
import { API_BASE_URL, WS_BASE_URL, WEDDING_SLUG } from "../../config";

interface Transfer {
  id: number;
  filename: string;
  status: string;
  progress: number;
  error_message: string | null;
}

export default function LiveTransfers() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);

  useEffect(() => {
    // Initial fetch
    const fetchTransfers = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/weddings/${WEDDING_SLUG}/photographer/transfers/`);
        if (res.ok) {
          const data = await res.json();
          setTransfers(data);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchTransfers();

    // WebSocket connection
    const ws = new WebSocket(`${WS_BASE_URL}/weddings/${WEDDING_SLUG}/`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transfer_update') {
        const updatedTransfer = data.transfer;
        setTransfers(prev => {
          const exists = prev.find(t => t.id === updatedTransfer.id);
          if (exists) {
            return prev.map(t => t.id === updatedTransfer.id ? updatedTransfer : t);
          } else {
            return [updatedTransfer, ...prev];
          }
        });
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Live Transfers</h1>
          <p className="text-neutral-400 mt-2">Real-time FTP upload queue.</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
        {transfers.length === 0 ? (
          <div className="p-12 text-center text-neutral-500 flex flex-col items-center">
            <ImageIcon className="w-12 h-12 mb-4 opacity-50" />
            <p>No transfers yet. Start shooting!</p>
          </div>
        ) : (
          <ul className="divide-y divide-neutral-800 max-h-[70vh] overflow-y-auto">
            {transfers.map((t) => (
              <li key={t.id} className="p-4 flex items-center justify-between hover:bg-neutral-800/50 transition-colors">
                <div className="flex items-center space-x-4">
                  <div className="p-2 bg-neutral-950 rounded-lg border border-neutral-800">
                    <ImageIcon className="w-5 h-5 text-neutral-400" />
                  </div>
                  <div>
                    <p className="font-medium text-neutral-200">{t.filename}</p>
                    <p className="text-xs text-neutral-500">Status: {t.status}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  {t.status === 'UPLOADING' && (
                    <div className="flex items-center space-x-2 text-orange-400 text-sm">
                      <Clock className="w-4 h-4 animate-spin" />
                      <span>{t.progress}%</span>
                    </div>
                  )}
                  {t.status === 'UPLOADED' && (
                    <div className="flex items-center space-x-2 text-blue-400 text-sm">
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      <span>Processing Face AI</span>
                    </div>
                  )}
                  {t.status === 'COMPLETED' && (
                    <div className="flex items-center space-x-2 text-emerald-400 text-sm">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Live in Gallery</span>
                    </div>
                  )}
                  {t.status === 'FAILED' && (
                    <div className="flex items-center space-x-2 text-rose-400 text-sm">
                      <XCircle className="w-4 h-4" />
                      <span>Failed</span>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
