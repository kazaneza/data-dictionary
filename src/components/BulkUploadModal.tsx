import React, { useState } from 'react';
import { X, Database, Table2 } from 'lucide-react';
import BulkTableUpload from './BulkTableUpload';
import BulkFieldUpload from './BulkFieldUpload';

interface BulkUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: Array<{ id: string; name: string }>;
  databases: Array<{ id: string; name: string; source_id: string }>;
  onSuccess: () => void;
}

export default function BulkUploadModal({
  isOpen,
  onClose,
  sources,
  databases,
  onSuccess
}: BulkUploadModalProps) {
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [selectedDatabaseId, setSelectedDatabaseId] = useState('');
  const [uploadType, setUploadType] = useState<'tables' | 'fields'>('tables');

  if (!isOpen) return null;

  const filteredDatabases = databases.filter(
    db => db.source_id === selectedSourceId
  );

  const handleSuccess = () => {
    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl">
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-semibold">Bulk Upload</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Source and Database Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source System
              </label>
              <select
                value={selectedSourceId}
                onChange={(e) => {
                  setSelectedSourceId(e.target.value);
                  setSelectedDatabaseId('');
                }}
                className="w-full rounded-lg border border-gray-300 px-4 py-2"
              >
                <option value="">Select Source System</option>
                {sources.map(source => (
                  <option key={source.id} value={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Database
              </label>
              <select
                value={selectedDatabaseId}
                onChange={(e) => setSelectedDatabaseId(e.target.value)}
                className={`w-full rounded-lg border border-gray-300 px-4 py-2 ${
                  !selectedSourceId ? 'bg-gray-100' : ''
                }`}
                disabled={!selectedSourceId}
              >
                <option value="">Select Database</option>
                {filteredDatabases.map(db => (
                  <option key={db.id} value={db.id}>
                    {db.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Upload Type Selection */}
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => setUploadType('tables')}
              className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                uploadType === 'tables'
                  ? 'bg-[#003B7E] text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Table2 className="h-5 w-5 mr-2" />
              Tables Upload
            </button>
            <button
              onClick={() => setUploadType('fields')}
              className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                uploadType === 'fields'
                  ? 'bg-[#003B7E] text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Database className="h-5 w-5 mr-2" />
              Fields Upload
            </button>
          </div>

          {/* Upload Component */}
          {uploadType === 'tables' ? (
            <BulkTableUpload
              selectedSourceId={selectedSourceId}
              selectedDatabaseId={selectedDatabaseId}
              onSuccess={handleSuccess}
            />
          ) : (
            <BulkFieldUpload
              selectedSourceId={selectedSourceId}
              selectedDatabaseId={selectedDatabaseId}
              onSuccess={handleSuccess}
            />
          )}
        </div>
      </div>
    </div>
  );
}