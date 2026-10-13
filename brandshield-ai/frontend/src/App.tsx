import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { SignUp } from './pages/SignUp';
import { Dashboard } from './pages/Dashboard';
import { BrandProfile } from './pages/BrandProfile';
import { SocialMonitoring } from './pages/SocialMonitoring';
import { AppMonitoring } from './pages/AppMonitoring';
import { Campaigns } from './pages/Campaigns';
import { Investigations } from './pages/Investigations';
import { Sources } from './pages/Sources';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />

          {/* Protected Application Routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="brand" element={<BrandProfile />} />
              <Route path="social" element={<SocialMonitoring />} />
              <Route path="apps" element={<AppMonitoring />} />
              <Route path="campaigns" element={<Campaigns />} />
              <Route path="investigations" element={<Investigations />} />
              <Route path="sources" element={<Sources />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
