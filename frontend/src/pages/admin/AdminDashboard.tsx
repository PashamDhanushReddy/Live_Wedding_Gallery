import { ImageIcon, Cloud, ScanFace, Eye, TrendingUp, AlertCircle } from "lucide-react";

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      {/* Live Banner */}
      <div className="bg-[#2a2424] rounded-2xl overflow-hidden flex flex-col md:flex-row relative">
        <div className="md:w-1/3 relative h-48 md:h-auto">
          <img 
            src="https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&q=80&w=800" 
            alt="Wedding" 
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent to-[#2a2424]"></div>
          <div className="absolute bottom-6 left-6 text-white">
            <h3 className="font-serif text-2xl mb-1">Sandeep Reddy<br/>& Prathyusha Reddy</h3>
            <p className="text-xs text-white/70">November 21, 2026</p>
          </div>
        </div>
        <div className="p-8 md:p-12 flex-1 flex flex-col justify-center text-white relative">
          <div className="flex items-center gap-2 bg-red-500/20 text-red-400 w-fit px-3 py-1 rounded-full text-xs font-medium mb-4 border border-red-500/30">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            LIVE
          </div>
          <h2 className="text-3xl md:text-4xl font-serif mb-2">Wedding Album is Live!</h2>
          <p className="text-white/70">Photos are being uploaded in real-time.</p>
          
          <div className="absolute right-8 bottom-8 text-primary font-serif italic text-2xl hidden lg:block opacity-50">
            Moments<br/>in Progress<br/>♡
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard 
          icon={<ImageIcon className="w-5 h-5 text-primary" />} 
          title="Photos Received" 
          value="2,438" 
          trend="+ 312 today" 
          trendColor="text-green-500" 
          iconBg="bg-primary/10"
        />
        <StatCard 
          icon={<Cloud className="w-5 h-5 text-green-600" />} 
          title="Photos Uploaded" 
          value="2,421" 
          trend="+ 288 today" 
          trendColor="text-green-500" 
          iconBg="bg-green-100"
        />
        <StatCard 
          icon={<ScanFace className="w-5 h-5 text-purple-600" />} 
          title="Faces Detected" 
          value="6,291" 
          trend="+ 842 today" 
          trendColor="text-green-500" 
          iconBg="bg-purple-100"
        />
        <StatCard 
          icon={<AlertCircle className="w-5 h-5 text-orange-600" />} 
          title="Failed Uploads" 
          value="3" 
          trend="- 5 today" 
          trendColor="text-green-500" 
          iconBg="bg-orange-100"
        />
        <StatCard 
          icon={<Eye className="w-5 h-5 text-blue-600" />} 
          title="Live Viewers" 
          value="128" 
          trend="+ 47 today" 
          trendColor="text-green-500" 
          iconBg="bg-blue-100"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-border">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-medium text-foreground">Photos Upload Trend</h3>
            <select className="bg-secondary text-sm border-none rounded-md px-3 py-1">
              <option>Today</option>
              <option>Yesterday</option>
            </select>
          </div>
          <div className="h-48 flex items-end justify-between gap-2">
            {/* Dummy Chart bars */}
            {[40, 70, 90, 150, 180, 120, 80, 50].map((h, i) => (
              <div key={i} className="w-full bg-primary/20 rounded-t-sm hover:bg-primary/40 transition-colors" style={{ height: `${(h/200)*100}%` }}></div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-4 px-2">
            <span>6 AM</span>
            <span>9 AM</span>
            <span>12 PM</span>
            <span>3 PM</span>
            <span>6 PM</span>
            <span>9 PM</span>
          </div>
        </div>

        {/* Storage */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-border flex flex-col">
          <h3 className="font-medium text-foreground mb-6">Storage Usage</h3>
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="relative w-32 h-32 mb-6">
              <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 36 36">
                <path className="text-secondary stroke-current" strokeWidth="4" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="text-primary stroke-current" strokeWidth="4" strokeDasharray="68, 100" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-foreground">68%</span>
              </div>
            </div>
            
            <div className="w-full space-y-3">
              <div className="flex justify-between text-sm">
                <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-primary"></span> Used Space</span>
                <span className="font-medium">342 GB</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-secondary"></span> Remaining</span>
                <span className="font-medium">158 GB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, title, value, trend, trendColor, iconBg }: any) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-border flex flex-col">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-2.5 rounded-xl ${iconBg}`}>
          {icon}
        </div>
      </div>
      <div>
        <h4 className="text-2xl font-bold text-foreground mb-1">{value}</h4>
        <p className="text-sm text-muted-foreground mb-3">{title}</p>
        <p className={`text-xs font-medium flex items-center gap-1 ${trendColor}`}>
          <TrendingUp className="w-3 h-3" /> {trend}
        </p>
      </div>
    </div>
  );
}
