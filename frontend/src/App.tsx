import { lazy, Suspense } from "react";
import { HashRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import PageLoadingFallback from "./components/ui/PageLoadingFallback";

// Route-level Code Splitting for optimal initial bundle size
const LandingPage = lazy(() => import("./pages/LandingPage"));
const GalleryPage = lazy(() => import("./pages/GalleryPage"));
const FindPhotosPage = lazy(() => import("./pages/FindPhotosPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const SharePage = lazy(() => import("./pages/SharePage"));

const PhotographerLogin = lazy(() => import("./pages/photographer/Login"));
const PhotographerLayout = lazy(() => import("./components/layout/PhotographerLayout"));
const PhotographerDashboard = lazy(() => import("./pages/photographer/Dashboard"));
const CameraConnection = lazy(() => import("./pages/photographer/CameraConnection"));
const LiveTransfers = lazy(() => import("./pages/photographer/LiveTransfers"));
const ManualUpload = lazy(() => import("./pages/photographer/ManualUpload"));
const AdminGallery = lazy(() => import("./pages/photographer/AdminGallery"));

const AdminLayout = lazy(() => import("./components/layout/AdminLayout"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard"));
const AdminLiveMonitor = lazy(() => import("./pages/admin/AdminLiveMonitor"));
const AdminPhotos = lazy(() => import("./pages/admin/AdminPhotos"));
const AdminFaces = lazy(() => import("./pages/admin/AdminFaces"));
const AdminSettings = lazy(() => import("./pages/admin/AdminSettings"));

function App() {
  return (
    <HashRouter>
      <Suspense fallback={<PageLoadingFallback />}>
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

          {/* Admin portal */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="live" element={<AdminLiveMonitor />} />
            <Route path="photos" element={<AdminPhotos />} />
            <Route path="faces" element={<AdminFaces />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
        </Routes>
      </Suspense>
    </HashRouter>
  );
}

export default App;
