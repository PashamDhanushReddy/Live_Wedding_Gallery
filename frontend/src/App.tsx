import { HashRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";

import LandingPage from "./pages/LandingPage";
import GalleryPage from "./pages/GalleryPage";
import FindPhotosPage from "./pages/FindPhotosPage";
import AboutPage from "./pages/AboutPage";
import SharePage from "./pages/SharePage";
import AdminLayout from "./components/layout/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminPhotos from "./pages/admin/AdminPhotos";
import AdminFaces from "./pages/admin/AdminFaces";
import AdminSettings from "./pages/admin/AdminSettings";

import PhotographerLayout from "./components/layout/PhotographerLayout";
import PhotographerDashboard from "./pages/photographer/Dashboard";
import CameraConnection from "./pages/photographer/CameraConnection";
import LiveTransfers from "./pages/photographer/LiveTransfers";
import ManualUpload from "./pages/photographer/ManualUpload";
import AdminGallery from "./pages/photographer/AdminGallery";
import PhotographerLogin from "./pages/photographer/Login";

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="photos" element={<GalleryPage />} />
          <Route path="find" element={<FindPhotosPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="share" element={<SharePage />} />
        </Route>
        
        {/* Photographer Portal */}
        <Route path="/photographer/login" element={<PhotographerLogin />} />
        
        <Route path="/photographer" element={<PhotographerLayout />}>
          <Route index element={<PhotographerDashboard />} />
          <Route path="camera" element={<CameraConnection />} />
          <Route path="transfers" element={<LiveTransfers />} />
          <Route path="upload" element={<ManualUpload />} />
          <Route path="manage" element={<AdminGallery />} />
        </Route>

        {/* Admin portal could have a different layout */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="photos" element={<AdminPhotos />} />
          <Route path="faces" element={<AdminFaces />} />
          <Route path="settings" element={<AdminSettings />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
