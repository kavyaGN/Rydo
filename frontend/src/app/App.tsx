import { lazy, Suspense, type ComponentType } from "react";
import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "../components/layout/ProtectedRoute";
import { RoleRoute } from "../components/layout/RoleRoute";
import { AuthPage } from "../routes/AuthPage";
import { LandingPage } from "../routes/LandingPage";

// Public entry pages load eagerly; every signed-in page is code-split so the
// first visit downloads only what the landing and login screens need.
function lazyPage<K extends string>(load: () => Promise<Record<K, ComponentType>>, name: K) {
  return lazy(() => load().then((module) => ({ default: module[name] })));
}

const AdminDashboardPage = lazyPage(() => import("../routes/AdminDashboardPage"), "AdminDashboardPage");
const DriverDashboardPage = lazyPage(() => import("../routes/DriverDashboardPage"), "DriverDashboardPage");
const HomePage = lazyPage(() => import("../routes/HomePage"), "HomePage");
const NotificationsPage = lazyPage(() => import("../routes/NotificationsPage"), "NotificationsPage");
const PaymentPage = lazyPage(() => import("../routes/PaymentPage"), "PaymentPage");
const ProfilePage = lazyPage(() => import("../routes/ProfilePage"), "ProfilePage");
const RatingsPage = lazyPage(() => import("../routes/RatingsPage"), "RatingsPage");
const RentPage = lazyPage(() => import("../routes/RentPage"), "RentPage");
const RideHistoryPage = lazyPage(() => import("../routes/RideHistoryPage"), "RideHistoryPage");
const RideTrackingPage = lazyPage(() => import("../routes/RideTrackingPage"), "RideTrackingPage");
const SettingsPage = lazyPage(() => import("../routes/SettingsPage"), "SettingsPage");

function PageLoader() {
  return (
    <div role="status" aria-live="polite" className="flex min-h-screen items-center justify-center text-sm text-neutral-500">
      Loading…
    </div>
  );
}

export function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/rent" element={<RentPage />} />
        <Route path="/:mode" element={<AuthPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<RoleRoute allow={["customer"]} />}>
            <Route path="/app" element={<HomePage />} />
            <Route path="/history" element={<RideHistoryPage />} />
            <Route path="/rides/:rideId/tracking" element={<RideTrackingPage />} />
            <Route path="/payment" element={<PaymentPage />} />
            <Route path="/ratings" element={<RatingsPage />} />
          </Route>
          <Route element={<RoleRoute allow={["driver"]} />}>
            <Route path="/driver" element={<DriverDashboardPage />} />
          </Route>
          <Route element={<RoleRoute allow={["admin"]} />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
          </Route>
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
