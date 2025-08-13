import React, { useEffect, useState } from 'react';
import { Database, Server, FileSpreadsheet, Network, ArrowUpRight, Plus, Settings as SettingsIcon, FolderCog } from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchDashboardStats, fetchSources, hasManageAccess, isAdmin } from '../lib/api';
import { toast } from 'react-hot-toast';

interface DashboardStats {
  total_sources: number;
  total_tables: number;
  total_fields: number;
  active_systems: number;
}

interface SourceSystem {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  status?: string;
}

function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    total_sources: 0,
    total_tables: 0,
    total_fields: 0,
    active_systems: 0
  });

  const [sources, setSources] = useState<SourceSystem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showContent, setShowContent] = useState(false);

  const canManage = hasManageAccess();
  const canAdmin = isAdmin();

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setError(null);
        const [statsData, sourcesData] = await Promise.all([
          fetchDashboardStats(),
          fetchSources()
        ]);
        
        setStats(statsData);
        setSources(sourcesData);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        setError('Failed to load dashboard data. Please try again later.');
        toast.error('Failed to load dashboard data');
      } finally {
        setLoading(false);
        setTimeout(() => setShowContent(true), 100);
      }
    };

    loadDashboardData();
  }, []);

  const statsData = [
    { 
      name: 'Data Sources', 
      value: stats.total_sources.toString(), 
      icon: Database,
      color: 'bg-gradient-to-br from-blue-500 to-blue-600',
      textColor: 'text-blue-600',
      bgLight: 'bg-blue-50'
    },
    { 
      name: 'Tables', 
      value: stats.total_tables.toString(), 
      icon: FileSpreadsheet,
      color: 'bg-gradient-to-br from-purple-500 to-purple-600',
      textColor: 'text-purple-600',
      bgLight: 'bg-purple-50'
    },
    { 
      name: 'Fields', 
      value: stats.total_fields.toString(), 
      icon: Server,
      color: 'bg-gradient-to-br from-green-500 to-green-600',
      textColor: 'text-green-600',
      bgLight: 'bg-green-50'
    },
    { 
      name: 'Active Databases', 
      value: stats.active_systems.toString(), 
      icon: Network,
      color: 'bg-gradient-to-br from-orange-500 to-orange-600',
      textColor: 'text-orange-600',
      bgLight: 'bg-orange-50'
    },
  ];

  // Updated quick links to only point to data dictionary
  const quickLinks = [
    {
      title: 'Browse Data Dictionary',
      description: 'Explore all data sources and structures',
      icon: Database,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      link: '/dictionary'
    },
    {
      title: 'View Tables',
      description: 'Browse all database tables',
      icon: FileSpreadsheet,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      link: '/dictionary'
    },
    {
      title: 'Explore Fields',
      description: 'View detailed field information',
      icon: Server,
      color: 'text-green-600',
      bg: 'bg-green-50',
      link: '/dictionary'
    }
  ];

  if (loading) {
    return (
      <div className="h-[calc(100vh-5rem)] flex items-center justify-center">
        <div className="relative">
          <div className="h-24 w-24 rounded-full border-t-4 border-b-4 border-[#003B7E] animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Database className="h-8 w-8 text-[#003B7E] animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-5rem)] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-[#003B7E] text-white px-6 py-2 rounded-lg hover:bg-[#002c5f] transition-all duration-300 transform hover:scale-105"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-5rem)] flex flex-col space-y-6 py-6">
      {/* Welcome Section */}
      <div 
        className={`bg-gradient-to-r from-[#003B7E] to-[#002c5f] rounded-xl p-6 text-white shadow-lg transform transition-all duration-700 ${
          showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
        }`}
      >
        <h1 className="text-2xl font-bold">Welcome to BK Data Dictionary</h1>
        <p className="text-blue-100 text-sm mt-1">
          Your central hub for managing and exploring database structures across all systems.
        </p>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-6">
        {/* Stats Overview */}
        <div className="col-span-12 grid grid-cols-4 gap-4">
          {statsData.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div 
                key={stat.name}
                className={`bg-white rounded-xl shadow-md overflow-hidden transform transition-all duration-700 hover:scale-105 ${
                  showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
                }`}
                style={{ transitionDelay: `${index * 100}ms` }}
              >
                <div className={`${stat.color} p-3`}>
                  <div className="flex items-center justify-between">
                    <div className={`${stat.bgLight} p-2 rounded-lg`}>
                      <Icon className={`h-5 w-5 ${stat.textColor}`} />
                    </div>
                  </div>
                </div>
                <div className="p-3">
                  <div className="flex flex-col">
                    <h3 className="text-2xl font-bold">{stat.value}</h3>
                    <p className="text-gray-600 text-xs">{stat.name}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Source Systems */}
        <div 
          className={`col-span-8 bg-white rounded-xl shadow-md overflow-hidden transform transition-all duration-700 ${
            showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
          }`}
          style={{ transitionDelay: '400ms' }}
        >
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Source Systems</h2>
              <Link 
                to="/dictionary" 
                className="text-[#003B7E] hover:text-[#004c9e] flex items-center group text-sm"
              >
                View All 
                <ArrowUpRight className="h-4 w-4 ml-1 transform transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" />
              </Link>
            </div>
            <div className="space-y-3">
              {sources.slice(0, 3).map((source, index) => (
                <div 
                  key={source.id} 
                  className={`flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-all duration-300 transform ${
                    showContent ? 'translate-x-0 opacity-100' : 'translate-x-10 opacity-0'
                  }`}
                  style={{ transitionDelay: `${500 + (index * 100)}ms` }}
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-[#003B7E] bg-opacity-10 rounded-lg">
                      <Server className="h-4 w-4 text-[#003B7E]" />
                    </div>
                    <div>
                      <h3 className="font-medium text-sm">{source.name}</h3>
                      {source.category && (
                        <span className="text-xs text-gray-500">{source.category}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                    Active
                  </span>
                </div>
              ))}
              {sources.length === 0 && (
                <div className="text-center py-6 text-gray-500">
                  <p className="text-sm mb-3">No source systems found</p>
                  {canManage && (
                    <Link 
                      to="/settings" 
                      className="inline-flex items-center px-3 py-1.5 bg-[#003B7E] text-white text-sm rounded-lg hover:bg-[#002c5f] transition-all duration-300"
                    >
                      Add Source System
                    </Link>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div 
          className={`col-span-4 bg-white rounded-xl shadow-md overflow-hidden transform transition-all duration-700 ${
            showContent ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'
          }`}
          style={{ transitionDelay: '600ms' }}
        >
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-4">Quick Links</h2>
            <div className="space-y-3">
              {quickLinks.map((link, index) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.title}
                    to={link.link}
                    className={`block p-3 rounded-lg ${link.bg} group hover:bg-opacity-70 transition-all duration-300 transform ${
                      showContent ? 'translate-x-0 opacity-100' : 'translate-x-10 opacity-0'
                    }`}
                    style={{ transitionDelay: `${700 + (index * 100)}ms` }}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`p-1.5 bg-white rounded-lg ${link.color}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="font-medium text-sm text-gray-900">{link.title}</h3>
                        <p className="text-xs text-gray-600">{link.description}</p>
                      </div>
                      <ArrowUpRight className={`h-4 w-4 ml-auto ${link.color} transform transition-transform group-hover:translate-x-1 group-hover:-translate-y-1`} />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;