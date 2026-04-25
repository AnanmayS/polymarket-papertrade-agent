import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { CandidatesPage } from "./pages/CandidatesPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { PostmortemsPage } from "./pages/PostmortemsPage";
import { ScannerPage } from "./pages/ScannerPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TradesPage } from "./pages/TradesPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<PortfolioPage />} />
        <Route path="markets" element={<ScannerPage />} />
        <Route path="ideas" element={<CandidatesPage />} />
        <Route path="trades" element={<TradesPage />} />
        <Route path="reviews" element={<PostmortemsPage />} />
        <Route path="rules" element={<SettingsPage />} />

        <Route path="scanner" element={<Navigate to="/markets" replace />} />
        <Route path="candidates" element={<Navigate to="/ideas" replace />} />
        <Route path="postmortems" element={<Navigate to="/reviews" replace />} />
        <Route path="settings" element={<Navigate to="/rules" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
