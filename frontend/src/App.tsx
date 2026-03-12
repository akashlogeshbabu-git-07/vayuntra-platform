// Vayuntra SOC Dashboard — Main Application Shell
// React 18 + TypeScript + Tailwind CSS

import { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { TenantProvider } from "@/hooks/useTenant";
import { WebSocketProvider } from "@/hooks/useWebSocket";
import { ThemeProvider } from "@/hooks/useTheme";
import { NotificationProvider } from "@/hooks/useNotifications";

import { AppLayout } from "@/components/shared/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ThreatsPage } from "@/pages/ThreatsPage";
import { ThreatDetailPage } from "@/pages/ThreatDetailPage";
import { AgentsPage } from "@/pages/AgentsPage";
import { RemediationPage } from "@/pages/RemediationPage";
import { BehavioralPage } from "@/pages/BehavioralPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { LoginPage } from "@/pages/LoginPage";
import { LoadingScreen } from "@/components/shared/LoadingScreen";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,         // 30 seconds
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="threats" element={<ThreatsPage />} />
        <Route path="threats/:id" element={<ThreatDetailPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="remediation" element={<RemediationPage />} />
        <Route path="behavioral" element={<BehavioralPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <TenantProvider>
            <WebSocketProvider>
              <NotificationProvider>
                <Router>
                  <AppRoutes />
                </Router>
              </NotificationProvider>
            </WebSocketProvider>
          </TenantProvider>
        </AuthProvider>
      </ThemeProvider>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
