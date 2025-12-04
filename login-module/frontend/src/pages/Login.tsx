import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { login } from '../lib/api';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setShowContent(true);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(username, password);
      
      // Animate out before redirecting
      setShowContent(false);
      setTimeout(() => {
        toast.success('Login successful!');
        window.location.href = '/';
      }, 500);
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Invalid credentials or server error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 overflow-hidden">
      <div 
        className={`sm:mx-auto sm:w-full sm:max-w-md transform transition-all duration-1000 ease-out ${
          showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
        }`}
      >
        <div className="flex justify-center mb-8">
          <div className="relative w-32 h-32">
            {/* Logo placeholder - replace with your logo */}
            <div className={`absolute inset-0 w-full h-full bg-blue-500 rounded-full flex items-center justify-center transform transition-all duration-1000 ${
              showContent ? 'scale-100 rotate-0 opacity-100' : 'scale-50 rotate-180 opacity-0'
            }`}>
              <User className="w-16 h-16 text-white" />
            </div>
            <div className={`absolute inset-0 bg-blue-500 rounded-full transform transition-all duration-1000 filter blur-2xl ${
              showContent ? 'scale-75 opacity-20' : 'scale-0 opacity-0'
            }`} />
          </div>
        </div>
        <h2 className={`mt-6 text-center text-3xl font-extrabold text-gray-900 transform transition-all duration-700 delay-300 ${
          showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
        }`}>
          Welcome
        </h2>
        <p className={`mt-2 text-center text-sm text-gray-600 transform transition-all duration-700 delay-500 ${
          showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
        }`}>
          Sign in with your credentials
        </p>
      </div>

      <div className={`mt-8 sm:mx-auto sm:w-full sm:max-w-md transform transition-all duration-1000 delay-700 ${
        showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
      }`}>
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-lg sm:px-10 relative overflow-hidden">
          {/* Animated background gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-indigo-50 opacity-50 transform rotate-12 scale-150" />
          
          <form className="space-y-6 relative" onSubmit={handleLogin}>
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-gray-700"
              >
                Username
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-shadow duration-200"
                  placeholder="Username"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-shadow duration-200"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="relative w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200 overflow-hidden group"
              >
                <span className={`absolute inset-0 w-full h-full transition-all duration-300 ease-out transform translate-x-0 -skew-x-12 bg-white group-hover:translate-x-full group-hover:scale-x-150 ${loading ? 'opacity-20' : 'opacity-10'}`} />
                <span className="relative">
                  {loading ? 'Signing in...' : 'Sign in'}
                </span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;

