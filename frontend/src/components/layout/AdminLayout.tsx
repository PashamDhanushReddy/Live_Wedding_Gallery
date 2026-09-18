import { Link, Outlet, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  Image as ImageIcon, 
  MonitorPlay, 
  ScanFace, 
  Cloud, 
  Users, 
  Settings,
  LogOut,
  Bell,
  ExternalLink
} from "lucide-react";

export default function AdminLayout() {
  const location = useLocation();

  const navItems = [
    { name: "Dashboard", path: "/admin", icon: LayoutDashboard },
    { name: "Photos", path: "/admin/photos", icon: ImageIcon },
    { name: "Live Monitor", path: "/admin/live", icon: MonitorPlay },
    { name: "Face Recognition", path: "/admin/faces", icon: ScanFace },
    { name: "Cloudinary Accounts", path: "/admin/cloudinary", icon: Cloud },
    { name: "Visitors", path: "/admin/visitors", icon: Users },
    { name: "Settings", path: "/admin/settings", icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-border flex flex-col hidden md:flex">
        <div className="p-6">
          <Link to="/admin" className="flex flex-col items-center gap-1 font-serif text-3xl font-bold tracking-tight text-center">
            <span>S <span className="text-primary text-xl">❤️</span> P</span>
            <span className="text-sm font-sans font-medium text-foreground tracking-normal mt-1">Wedding Album</span>
            <span className="text-xs font-sans text-muted-foreground font-normal tracking-normal">Admin Portal</span>
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  isActive 
                    ? "bg-primary text-primary-foreground shadow-sm" 
                    : "text-foreground hover:bg-secondary"
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? "text-primary-foreground" : "text-muted-foreground"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border mt-auto">
          <div className="flex items-center gap-3 px-4 py-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
              SR
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-medium truncate">Sandeep Reddy</p>
              <p className="text-xs text-muted-foreground">Admin</p>
            </div>
          </div>
          <button className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-foreground hover:bg-secondary w-full transition-colors">
            <LogOut className="w-5 h-5 text-muted-foreground" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[#faf8f6]">
        {/* Topbar */}
        <header className="h-20 bg-white border-b border-border flex items-center justify-between px-8 shrink-0">
          <div>
            <h2 className="font-semibold text-lg flex items-center gap-2">
              Sandeep Reddy <span className="text-primary text-xs">❤️</span> Prathyusha Reddy
            </h2>
            <p className="text-xs text-muted-foreground">November 21, 2026 | Nizamabad, Telangana</p>
          </div>

          <div className="flex items-center gap-6">
            <button className="relative text-foreground hover:text-primary transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
            </button>
            <Link 
              to="/" 
              target="_blank"
              className="flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
            >
              View Live Site
              <ExternalLink className="w-4 h-4" />
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
