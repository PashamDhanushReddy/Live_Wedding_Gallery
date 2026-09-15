import { Search, SlidersHorizontal, Grid, List, CheckCircle2, AlertCircle, Clock, UploadCloud, ChevronDown, MoreVertical } from "lucide-react";
import { useState } from "react";

const mockPhotos = [
  { id: "IMG_4832.JPG", date: "Nov 21, 2026 11:42 AM", size: "4.2 MB", status: "Published", url: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4833.JPG", date: "Nov 21, 2026 11:42 AM", size: "3.8 MB", status: "Published", url: "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4834.JPG", date: "Nov 21, 2026 11:43 AM", size: "4.1 MB", status: "Published", url: "https://images.unsplash.com/photo-1532712938310-34cb3982ef74?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4835.JPG", date: "Nov 21, 2026 11:43 AM", size: "5.2 MB", status: "Processing", url: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4836.JPG", date: "Nov 21, 2026 11:43 AM", size: "4.6 MB", status: "Published", url: "https://images.unsplash.com/photo-1522673607200-164d1b6ce486?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4837.JPG", date: "Nov 21, 2026 11:43 AM", size: "3.1 MB", status: "Published", url: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4838.JPG", date: "Nov 21, 2026 11:44 AM", size: "4.0 MB", status: "Failed", url: "https://images.unsplash.com/photo-1519225421980-715cb0215aed?auto=format&fit=crop&q=80&w=400" },
  { id: "IMG_4839.JPG", date: "Nov 21, 2026 11:44 AM", size: "4.3 MB", status: "Published", url: "https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&q=80&w=400" },
];

export default function AdminPhotos() {
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string) => {
    const newSet = new Set(selectedPhotos);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedPhotos(newSet);
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-border">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 text-primary rounded-xl">
            <ImageIcon className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-serif text-foreground">Manage Photos</h1>
            <p className="text-muted-foreground text-sm">View, search, filter, and manage all uploaded photos.</p>
          </div>
        </div>
        <div className="flex gap-3 w-full sm:w-auto">
          <button className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-white border border-border px-4 py-2 rounded-lg font-medium hover:bg-secondary transition-colors">
            <UploadCloud className="w-4 h-4" />
            Upload Photos
          </button>
          <button className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium hover:bg-primary/90 transition-colors">
            Bulk Actions
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<ImageIcon />} title="Total Photos" value="2,438" color="text-primary" bg="bg-primary/10" />
        <StatCard icon={<CheckCircle2 />} title="Published" value="2,421" color="text-green-600" bg="bg-green-100" />
        <StatCard icon={<Clock />} title="Processing" value="7" color="text-blue-600" bg="bg-blue-100" />
        <StatCard icon={<AlertCircle />} title="Failed" value="3" color="text-red-600" bg="bg-red-100" />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 bg-white p-4 rounded-xl shadow-sm border border-border">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search photos (file name, people, tags...)" 
            className="w-full pl-9 pr-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="flex gap-3 overflow-x-auto hide-scrollbar">
          <select className="px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm outline-none min-w-[120px]">
            <option>All Events</option>
            <option>Ceremony</option>
            <option>Reception</option>
          </select>
          <select className="px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm outline-none min-w-[120px]">
            <option>All Status</option>
            <option>Published</option>
            <option>Processing</option>
            <option>Failed</option>
          </select>
          <select className="px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm outline-none min-w-[140px]">
            <option>Date (Newest)</option>
            <option>Date (Oldest)</option>
          </select>
          <div className="flex items-center p-1 bg-secondary/50 border border-border rounded-lg">
            <button className="p-1.5 bg-primary text-primary-foreground rounded-md shadow-sm">
              <Grid className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground">
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Photo Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {mockPhotos.map((photo) => (
          <div key={photo.id} className="bg-white rounded-xl overflow-hidden shadow-sm border border-border group">
            <div className="relative aspect-video">
              <img src={photo.url} alt={photo.id} className="w-full h-full object-cover" />
              <div className="absolute top-2 left-2">
                <input 
                  type="checkbox" 
                  checked={selectedPhotos.has(photo.id)}
                  onChange={() => toggleSelect(photo.id)}
                  className="w-4 h-4 rounded text-primary focus:ring-primary"
                />
              </div>
              <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <button className="p-2 bg-white rounded-full hover:bg-primary hover:text-white transition-colors">
                  <Eye className="w-4 h-4" />
                </button>
                <button className="p-2 bg-white rounded-full hover:bg-primary hover:text-white transition-colors">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-sm truncate pr-2">{photo.id}</h3>
                <button className="text-muted-foreground hover:text-foreground">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-3">{photo.date}</p>
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">{photo.size}</span>
                <span className={`px-2 py-1 rounded-full font-medium ${
                  photo.status === 'Published' ? 'bg-green-100 text-green-700' :
                  photo.status === 'Processing' ? 'bg-blue-100 text-blue-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {photo.status}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ icon, title, value, color, bg }: any) {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-border flex items-center gap-4">
      <div className={`p-3 rounded-lg ${bg} ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-foreground">{value}</p>
        <p className="text-sm text-muted-foreground">{title}</p>
      </div>
    </div>
  );
}
