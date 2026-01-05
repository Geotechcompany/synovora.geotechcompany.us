import { useEffect, useRef } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth, useUser } from '@clerk/clerk-react';

import DashboardPage from './pages/Dashboard';
import AuthPage from './pages/Auth';
import SettingsPage from './pages/Settings';
import { syncClerkUser } from './lib/api';
import { AppShellSkeleton } from './components/app-shell-skeleton';

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { isLoaded, isSignedIn } = useAuth();
  const { user, isLoaded: isUserLoaded } = useUser();
  const lastSyncedSnapshot = useRef<string | null>(null);

  useEffect(() => {
    if (!user || !isSignedIn) return;

    const snapshot = `${user.id}-${user.updatedAt?.toISOString?.() ?? ''}`;
    if (lastSyncedSnapshot.current === snapshot) return;
    lastSyncedSnapshot.current = snapshot;

    syncClerkUser({
      clerk_user_id: user.id,
      email: user.primaryEmailAddress?.emailAddress ?? undefined,
      first_name: user.firstName ?? undefined,
      last_name: user.lastName ?? undefined,
      username: user.username ?? undefined,
      image_url: user.imageUrl ?? undefined,
      external_id: user.externalId ?? undefined,
      last_sign_in_at: user.lastSignInAt?.toISOString?.(),
      created_at: user.createdAt?.toISOString?.(),
    }).catch((error) => {
      console.error('Failed to sync Clerk user', error);
    });
  }, [user, isSignedIn]);

  if (!isLoaded || !isUserLoaded) {
    return <AppShellSkeleton />;
  }

  if (!isSignedIn || !user) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
