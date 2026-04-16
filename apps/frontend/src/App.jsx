import { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Home from './pages/Home';
import Public from './pages/Public';
import Callback from './pages/Callback';
import { checkAuth, refreshSession } from './services/auth';

const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth().then((userData) => {
      setUser(userData);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!user) return;

    const REFRESH_INTERVAL = 4 * 60 * 1000;

    const interval = setInterval(async () => {
      try {
        await refreshSession();
        console.log('Session refreshed');
      } catch (error) {
        console.error('Session refresh failed:', error);
        setUser(null);
      }
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [user]);

  const logout = async () => {
    const { logout: authLogout } = await import('./services/auth');
    await authLogout();
    setUser(null);
  };

  if (loading) {
    return <div style={loadingStyle}>Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
          <Route path="/callback" element={<Callback />} />
          <Route path="/public" element={<Public />} />
          <Route path="/" element={user ? <Home /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

const loadingStyle = {
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: '100vh',
};

export default App;