import { Link, Outlet, useLocation, Navigate, useNavigate } from "react-router-dom";
import { Camera, Activity, LayoutDashboard, LogOut, UploadCloud } from "lucide-react";
import clsx from "clsx";

export default function PhotographerLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const token = localStorage.getItem("photographer_token");

  if (!token) {
    return <Navigate to="/photographer/login" replace />;
  }

  const navItems = [
    { name: "Dashboard", path: "/photographer", icon: LayoutDashboard },
    { name: "Camera", path: "/photographer/camera", icon: Camera },
    { name: "Live Transfers", path: "/photographer/transfers", icon: Activity },
    { name: "Manual Upload", path: "/photographer/upload", icon: UploadCloud },
    { name: "Manage Photos", path: "/photographer/manage", icon: Camera },
  ];

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col">
        <div className="p-6 border-b border-neutral-800">
          <h2 className="text-xl font-bold tracking-tight bg-gradient-to-r from-rose-400 to-orange-400 bg-clip-text text-transparent">
            Photographer Pro
          </h2>
          <p className="text-xs text-neutral-400 mt-1">Live Ingestion</p>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/photographer' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.name}
                to={item.path}
                className={clsx(
                  "flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors duration-200",
                  isActive
                    ? "bg-rose-500/10 text-rose-400 font-medium"
                    : "text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200"
                )}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-neutral-800 space-y-2">
          <button
            onClick={() => {
              localStorage.removeItem("photographer_token");
              navigate("/photographer/login");
            }}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-neutral-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Sign Out</span>
          </button>
          <Link
            to="/"
            className="flex items-center space-x-3 px-4 py-3 rounded-xl text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span>Exit to Gallery</span>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-8 overflow-y-auto">
        <div className="max-w-5xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
