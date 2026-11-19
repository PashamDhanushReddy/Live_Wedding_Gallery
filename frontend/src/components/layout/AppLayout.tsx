import { Outlet } from "react-router-dom";
import Header from "./Header";
import CameraPermissionModal from "../ui/CameraPermissionModal";

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background font-sans text-foreground">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <CameraPermissionModal />
    </div>
  );
}
