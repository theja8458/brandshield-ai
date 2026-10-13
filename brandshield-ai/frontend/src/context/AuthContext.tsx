import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthContextType, User } from '../types/auth';
import {
  fetchCurrentUser,
  loginUser,
  logoutUser,
} from '../api/authClient';
import {
  getStoredToken,
  getStoredUser,
  setStoredToken,
} from '../api/apiClient';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<User | null>(getStoredUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    const verifySession = async () => {
      const activeToken = getStoredToken();
      if (!activeToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await fetchCurrentUser();
        if (isMounted) {
          setUser(currentUser);
          setToken(activeToken);
        }
      } catch (err) {
        console.warn('Session verification failed, logging out:', err);
        if (isMounted) {
          setStoredToken(null);
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    verifySession();

    // Listen for 401 unauthorized events dispatched by apiClient
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('brandshield:unauthorized', handleUnauthorized);
    return () => {
      isMounted = false;
      window.removeEventListener('brandshield:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (email: string, pass: string): Promise<void> => {
    const res = await loginUser(email, pass);
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = async (): Promise<void> => {
    await logoutUser();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(token && user),
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
