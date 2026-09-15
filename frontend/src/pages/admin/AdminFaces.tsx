import { ScanFace, ImageIcon, Users, AlertCircle, TrendingUp, RefreshCw, Settings } from "lucide-react";

export default function AdminFaces() {
  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-border">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-purple-100 text-purple-600 rounded-xl">
            <ScanFace className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-serif text-foreground">Face Recognition</h1>
            <p className="text-muted-foreground text-sm">Monitor face detection, search results, and manage face data.</p>
          </div>
        </div>
        <div className="flex gap-3 w-full sm:w-auto">
          <button className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-white border border-border px-4 py-2 rounded-lg font-medium hover:bg-secondary transition-colors">
            <RefreshCw className="w-4 h-4" />
            Reprocess All
          </button>
          <button className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium hover:bg-primary/90 transition-colors">
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          icon={<ScanFace />} title="Faces Detected" value="6,291" 
          trend="+ 842 today" trendColor="text-green-500" 
          color="text-purple-600" bg="bg-purple-100" 
        />
        <StatCard 
          icon={<ImageIcon />} title="Photos Indexed" value="2,438" 
          trend="+ 312 today" trendColor="text-green-500" 
          color="text-green-600" bg="bg-green-100" 
        />
        <StatCard 
          icon={<Users />} title="Unique People" value="684" 
          trend="+ 21 today" trendColor="text-green-500" 
          color="text-blue-600" bg="bg-blue-100" 
        />
        <StatCard 
          icon={<AlertCircle />} title="Failed Detections" value="17" 
          trend="- 5 today" trendColor="text-green-500" 
          color="text-red-600" bg="bg-red-100" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-border">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-medium text-foreground">Face Detection Trend</h3>
            <select className="bg-secondary text-sm border-none rounded-md px-3 py-1">
              <option>Last 24 Hours</option>
              <option>Last 7 Days</option>
            </select>
          </div>
          <div className="h-48 flex items-end justify-between gap-2">
            {[40, 70, 90, 150, 180, 220, 260, 300, 240, 180, 120, 80].map((h, i) => (
              <div key={i} className="flex-1 flex gap-1 items-end h-full">
                <div className="flex-1 bg-primary/20 rounded-t-sm hover:bg-primary/40 transition-colors" style={{ height: `${(h/300)*100}%` }}></div>
                <div className="flex-1 bg-primary/40 rounded-t-sm hover:bg-primary/60 transition-colors" style={{ height: `${((h*0.8)/300)*100}%` }}></div>
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-4 px-2">
            <span>12 AM</span>
            <span>4 AM</span>
            <span>8 AM</span>
            <span>12 PM</span>
            <span>4 PM</span>
            <span>8 PM</span>
          </div>
          <div className="flex justify-center gap-6 mt-4 pt-4 border-t border-border text-sm">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-primary/20"></span> Faces Detected
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-primary/40"></span> Photos Processed
            </div>
          </div>
        </div>

        {/* Top People & Status */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-border">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium text-foreground">Top People Detected</h3>
              <button className="text-primary text-sm font-medium hover:underline">View All</button>
            </div>
            <div className="space-y-4">
              {[
                { name: "Person 1", count: 412 },
                { name: "Person 2", count: 389 },
                { name: "Person 3", count: 321 },
                { name: "Person 4", count: 298 },
                { name: "Person 5", count: 276 },
              ].map((p, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-secondary overflow-hidden">
                      <img src={`https://i.pravatar.cc/150?img=${i+10}`} alt={p.name} className="w-full h-full object-cover" />
                    </div>
                    <div>
                      <p className="font-medium text-sm text-foreground">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.count} photos</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Detections */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-border">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-medium text-foreground">Recent Detections</h3>
          <button className="text-primary text-sm font-medium hover:underline">View All</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {[
            { img: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=400", faces: 3, id: "IMG_4832.JPG" },
            { img: "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?auto=format&fit=crop&q=80&w=400", faces: 5, id: "IMG_4833.JPG" },
            { img: "https://images.unsplash.com/photo-1532712938310-34cb3982ef74?auto=format&fit=crop&q=80&w=400", faces: 2, id: "IMG_4834.JPG" },
            { img: "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&q=80&w=400", faces: 4, id: "IMG_4835.JPG" },
            { img: "https://images.unsplash.com/photo-1522673607200-164d1b6ce486?auto=format&fit=crop&q=80&w=400", faces: 6, id: "IMG_4836.JPG" },
            { img: "https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&q=80&w=400", faces: 2, id: "IMG_4837.JPG" },
          ].map((item, i) => (
            <div key={i} className="group relative">
              <div className="relative aspect-square rounded-xl overflow-hidden mb-2">
                <img src={item.img} alt={item.id} className="w-full h-full object-cover" />
                {/* Bounding box simulation */}
                <div className="absolute top-1/4 left-1/4 w-1/4 h-1/4 border-2 border-green-500 rounded-sm"></div>
              </div>
              <p className="text-sm font-medium text-foreground truncate">{item.id}</p>
              <div className="flex justify-between items-center mt-1">
                <p className="text-xs text-muted-foreground">11:42:01 AM</p>
                <p className="text-xs text-muted-foreground">{item.faces} faces</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, title, value, trend, trendColor, color, bg }: any) {
  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-border flex items-center gap-4">
      <div className={`p-3 rounded-lg ${bg} ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-foreground">{value}</p>
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className={`text-xs font-medium flex items-center gap-1 mt-1 ${trendColor}`}>
          <TrendingUp className="w-3 h-3" /> {trend}
        </p>
      </div>
    </div>
  );
}
