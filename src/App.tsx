import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { Settings as SettingsIcon, LayoutDashboard, Database, FolderCog, LogOut, Link2, Search, Sparkles } from 'lucide-react';
import { Toaster } from 'react-hot-toast';
import Dashboard from './pages/Dashboard';
import DataDictionary from './pages/DataDictionary';
import SearchPage from './pages/Search';
import Settings from './pages/Settings';
import Manage from './pages/Manage';
import Login from './pages/Login';
import DatabaseImport from './pages/DatabaseImport';
import AIFieldFinder from './components/AIFieldFinder';
import { hasManageAccess, isAdmin } from './lib/api';

function PrivateRoute({ children, requiresManage = false, requiresAdmin = false }: { 
  children: React.ReactNode;
  requiresManage?: boolean;
  requiresAdmin?: boolean;
}) {
  const isAuthenticated = !!localStorage.getItem('authToken');
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (requiresAdmin && !isAdmin()) {
    return <Navigate to="/" />;
  }

  if (requiresManage && !hasManageAccess()) {
    return <Navigate to="/" />;
  }

  return <>{children}</>;
}

function NavLink({ to, children, show = true }: { 
  to: string; 
  children: React.ReactNode;
  show?: boolean;
}) {
  const location = useLocation();
  const isActive = location.pathname === to;
  
  if (!show) return null;

  return (
    <Link
      to={to}
      className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-all duration-200 ${
        isActive
          ? 'bg-white/10 text-white'
          : 'text-white/80 hover:bg-white/10 hover:text-white'
      }`}
    >
      {children}
    </Link>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));
  const [isScrolled, setIsScrolled] = useState(false);
  const canManage = hasManageAccess();
  const canAdmin = isAdmin();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleStorageChange = () => {
      setIsAuthenticated(!!localStorage.getItem('authToken'));
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  useEffect(() => {
    setIsAuthenticated(!!localStorage.getItem('authToken'));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userRole');
    setIsAuthenticated(false);
    window.location.href = '/login';
  };

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-gray-50">
        {isAuthenticated && (
          <header 
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
              isScrolled 
                ? 'bg-[#003B7E]/95 backdrop-blur-sm shadow-lg' 
                : 'bg-[#003B7E]'
            }`}
          >
            <div className="container mx-auto h-14 flex items-center justify-between px-4">
              <Link to="/" className="flex items-center space-x-2">
                <Database className="h-6 w-6 text-white" />
                <h1 className="text-lg font-bold text-white">
                  Data Dictionary
                </h1>
              </Link>

              <nav className="hidden md:flex items-center space-x-1">
                <NavLink to="/">
                  <LayoutDashboard className="h-4 w-4" />
                  <span>Dashboard</span>
                </NavLink>
                <NavLink to="/dictionary">
                  <Database className="h-4 w-4" />
                  <span>Data Dictionary</span>
                </NavLink>
                <NavLink to="/search">
                  <Search className="h-4 w-4" />
                  <span>Search</span>
                </NavLink>
                <NavLink to="/ai-field-finder">
                  <Sparkles className="h-4 w-4" />
                  <span>AI Field Finder</span>
                </NavLink>
                <NavLink to="/manage" show={canManage}>
                  <FolderCog className="h-4 w-4" />
                  <span>Manage</span>
                </NavLink>
                <NavLink to="/database-import" show={canAdmin}>
                  <Link2 className="h-4 w-4" />
                  <span>Import DB</span>
                </NavLink>
                <NavLink to="/settings" show={canAdmin}>
                  <SettingsIcon className="h-4 w-4" />
                  <span>Settings</span>
                </NavLink>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-3 py-2 rounded-lg text-white/80 hover:bg-white/10 hover:text-white transition-all duration-200"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </nav>
            </div>
          </header>
        )}

        <main className={`container mx-auto px-4 flex-grow ${isAuthenticated ? 'pt-20' : ''}`}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Dashboard />
                </PrivateRoute>
              }
            />
            <Route
              path="/dictionary"
              element={
                <PrivateRoute>
                  <DataDictionary />
                </PrivateRoute>
              }
            />
            <Route
              path="/search"
              element={
                <PrivateRoute>
                  <SearchPage />
                </PrivateRoute>
              }
            />
            <Route
              path="/ai-field-finder"
              element={
                <PrivateRoute>
                  <AIFieldFinder />
                </PrivateRoute>
              }
            />
            <Route
              path="/manage"
              element={
                <PrivateRoute requiresManage>
                  <Manage />
                </PrivateRoute>
              }
            />
            <Route
              path="/database-import"
              element={
                <PrivateRoute requiresAdmin>
                  <DatabaseImport />
                </PrivateRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <PrivateRoute requiresAdmin>
                  <Settings />
                </PrivateRoute>
              }
            />
          </Routes>
        </main>

        {isAuthenticated && (
          <footer className="mt-auto py-3 text-center text-sm text-gray-500 border-t">
            <p>For more information, contact Data Management Department</p>
          </footer>
        )}
      </div>
      <Toaster position="top-right" />
    </Router>
  );
}

export default App;