import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";

import LandingPage from "./pages/LandingPage";
import GalleryPage from "./pages/GalleryPage";
import FindPhotosPage from "./pages/FindPhotosPage";
import AdminLayout from "./components/layout/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminPhotos from "./pages/admin/AdminPhotos";
import AdminFaces from "./pages/admin/AdminFaces";
import AdminSettings from "./pages/admin/AdminSettings";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="photos" element={<GalleryPage />} />
          <Route path="find" element={<FindPhotosPage />} />
        </Route>
        {/* Admin portal could have a different layout */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="photos" element={<AdminPhotos />} />
          <Route path="faces" element={<AdminFaces />} />
          <Route path="settings" element={<AdminSettings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
