import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  Trash2,
  Database,
  Calendar,
  Play
} from 'lucide-react';
import { toast } from 'react-hot-toast';

interface ConnectionHistoryItem {
  id: string;
  timestamp: number;
  config: {
    server: string;
    database: string;
    username: string;
    type: string;
    source_id: string;
    description: string;
    platform: string;
    location: string;
    version: string;
  };
  status: 'success' | 'failed' | 'in_progress' | 'partial';
  totalTables: number;
  importedTables: number;
  failedTables: string[];
  errorMessage?: string;
  duration?: number;
}

interface ConnectionHistoryProps {
  onReconnect: (config: any) => void;
  onResume: (historyItem: ConnectionHistoryItem) => void;
  sources: Array<{ id: string; name: string }>;
}

const HISTORY_STORAGE_KEY = 'database_import_history';

export default function ConnectionHistory({ 
  onReconnect, 
  onResume, 
  sources 
}: ConnectionHistoryProps) {
  const [history, setHistory] = useState<ConnectionHistoryItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ConnectionHistoryItem | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    try {
      const savedHistory = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (savedHistory) {
        const parsed = JSON.parse(savedHistory);
        // Sort by timestamp, newest first
        const sorted = parsed.sort((a: ConnectionHistoryItem, b: ConnectionHistoryItem) => 
          b.timestamp - a.timestamp
        );
        setHistory(sorted);
      }
    } catch (error) {
      console.error('Failed to load connection history:', error);
    }
  };

  const clearHistory = () => {
    if (window.confirm('Are you sure you want to clear all connection history?')) {
      localStorage.removeItem(HISTORY_STORAGE_KEY);
      setHistory([]);
      setSelectedItem(null);
      toast.success('Connection history cleared');
    }
  };

  const deleteHistoryItem = (id: string) => {
    const updatedHistory = history.filter(item => item.id !== id);
    setHistory(updatedHistory);
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updatedHistory));
    if (selectedItem?.id === id) {
      setSelectedItem(null);
    }
    toast.success('History item deleted');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'in_progress':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'partial':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (item: ConnectionHistoryItem) => {
    switch (item.status) {
      case 'success':
        return `Successfully imported ${item.importedTables}/${item.totalTables} tables`;
      case 'failed':
        return `Failed: ${item.errorMessage || 'Unknown error'}`;
      case 'in_progress':
        return `In progress: ${item.importedTables}/${item.totalTables} tables imported`;
      case 'partial':
        return `Partial: ${item.importedTables}/${item.totalTables} tables imported, ${item.failedTables.length} failed`;
      default:
        return 'Unknown status';
    }
  };

  const formatDuration = (duration?: number) => {
    if (!duration) return 'N/A';
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const getSourceName = (sourceId: string) => {
    const source = sources.find(s => s.id === sourceId);
    return source?.name || 'Unknown Source';
  };

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Database className="h-12 w-12 mx-auto mb-4 text-gray-300" />
        <p>No connection history yet</p>
        <p className="text-sm">Your database connections will appear here</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Connection History</h3>
        <button
          onClick={clearHistory}
          className="text-red-600 hover:text-red-800 text-sm flex items-center space-x-1"
        >
          <Trash2 className="h-4 w-4" />
          <span>Clear All</span>
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {history.map((item) => (
          <div
            key={item.id}
            className={`border rounded-lg p-4 cursor-pointer transition-all ${
              selectedItem?.id === item.id 
                ? 'border-[#003B7E] bg-blue-50' 
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setSelectedItem(selectedItem?.id === item.id ? null : item)}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3">
                {getStatusIcon(item.status)}
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium text-gray-900">
                      {item.config.database}
                    </h4>
                    <span className="text-sm text-gray-500">
                      ({item.config.type})
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {getSourceName(item.config.source_id)} • {item.config.server}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {getStatusText(item)}
                  </p>
                  <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
                    <div className="flex items-center space-x-1">
                      <Calendar className="h-3 w-3" />
                      <span>{new Date(item.timestamp).toLocaleString()}</span>
                    </div>
                    {item.duration && (
                      <div className="flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>{formatDuration(item.duration)}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {(item.status === 'failed' || item.status === 'partial') && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onResume(item);
                    }}
                    className="text-blue-600 hover:text-blue-800 text-sm flex items-center space-x-1"
                    title="Resume import"
                  >
                    <Play className="h-4 w-4" />
                    <span>Resume</span>
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onReconnect(item.config);
                  }}
                  className="text-[#003B7E] hover:text-[#002c5f] text-sm flex items-center space-x-1"
                  title="Reconnect"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Reconnect</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteHistoryItem(item.id);
                  }}
                  className="text-red-600 hover:text-red-800"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Expanded Details */}
            {selectedItem?.id === item.id && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <h5 className="font-medium text-gray-700 mb-2">Connection Details</h5>
                    <div className="space-y-1 text-gray-600">
                      <p><span className="font-medium">Server:</span> {item.config.server}</p>
                      <p><span className="font-medium">Database:</span> {item.config.database}</p>
                      <p><span className="font-medium">Username:</span> {item.config.username}</p>
                      <p><span className="font-medium">Platform:</span> {item.config.platform}</p>
                      <p><span className="font-medium">Location:</span> {item.config.location}</p>
                      <p><span className="font-medium">Version:</span> {item.config.version}</p>
                    </div>
                  </div>
                  <div>
                    <h5 className="font-medium text-gray-700 mb-2">Import Status</h5>
                    <div className="space-y-1 text-gray-600">
                      <p><span className="font-medium">Total Tables:</span> {item.totalTables}</p>
                      <p><span className="font-medium">Imported:</span> {item.importedTables}</p>
                      {item.failedTables.length > 0 && (
                        <p><span className="font-medium">Failed:</span> {item.failedTables.length}</p>
                      )}
                      {item.errorMessage && (
                        <p><span className="font-medium">Error:</span> {item.errorMessage}</p>
                      )}
                    </div>
                  </div>
                </div>

                {item.failedTables.length > 0 && (
                  <div className="mt-4">
                    <h5 className="font-medium text-gray-700 mb-2">Failed Tables</h5>
                    <div className="flex flex-wrap gap-2">
                      {item.failedTables.map((tableName) => (
                        <span
                          key={tableName}
                          className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full"
                        >
                          {tableName}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Export utility functions for managing history
export const saveConnectionHistory = (historyItem: ConnectionHistoryItem) => {
  try {
    const existingHistory = JSON.parse(
      localStorage.getItem(HISTORY_STORAGE_KEY) || '[]'
    );
    
    // Update existing item or add new one
    const existingIndex = existingHistory.findIndex(
      (item: ConnectionHistoryItem) => item.id === historyItem.id
    );
    
    if (existingIndex >= 0) {
      existingHistory[existingIndex] = historyItem;
    } else {
      existingHistory.unshift(historyItem);
    }
    
    // Keep only last 50 items
    const trimmedHistory = existingHistory.slice(0, 50);
    
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(trimmedHistory));
  } catch (error) {
    console.error('Failed to save connection history:', error);
  }
};

export const createHistoryItem = (
  config: any,
  status: ConnectionHistoryItem['status'],
  totalTables: number = 0,
  importedTables: number = 0,
  failedTables: string[] = [],
  errorMessage?: string,
  duration?: number
): ConnectionHistoryItem => {
  return {
    id: `${config.server}_${config.database}_${Date.now()}`,
    timestamp: Date.now(),
    config,
    status,
    totalTables,
    importedTables,
    failedTables,
    errorMessage,
    duration
  };
};