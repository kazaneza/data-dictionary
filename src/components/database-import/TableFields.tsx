import React from 'react';
import { Save } from 'lucide-react';
import { SourceSystem } from '../../lib/api';
import TableFields from './TableFields';

interface SchemaPreviewProps {
  previewData: {
    tables: string[];
    fields: any[];
  } | null;
  config: {
    source_id: string;
    database: string;
    type: string;
    platform: string;
    location: string;
    version: string;
  };
  sources: SourceSystem[];
  selectedTable: string | null;
  tableFields: any[];
  loading: boolean;
  loadingDescriptions: boolean;
  onTableSelect: (table: string) => void;
  onImport: () => void;
}

export default function SchemaPreview({
  previewData,
  config,
  sources,
  selectedTable,
  tableFields,
  loading,
  loadingDescriptions,
  onTableSelect,
  onImport
}: SchemaPreviewProps) {
  if (!previewData) {
    return (
      <div className="text-center py-12 text-gray-500">
        Connect to a database to preview its schema
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mb-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium mb-2">Database Information</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-600">
              Source: {sources.find((s) => s.id === config.source_id)?.name}
            </p>
            <p className="text-gray-600">Database: {config.database}</p>
            <p className="text-gray-600">Type: {config.type}</p>
          </div>
          <div>
            <p className="text-gray-600">Platform: {config.platform}</p>
            <p className="text-gray-600">Location: {config.location}</p>
            <p className="text-gray-600">Version: {config.version}</p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="font-medium mb-4">
          Available Tables ({previewData.tables.length})
        </h3>
        <div className="grid grid-cols-3 gap-4">
          {previewData.tables.map((table) => (
            <div
              key={table}
              onClick={() => onTableSelect(table)}
              className={`p-3 bg-gray-50 rounded-lg cursor-pointer transition-colors ${
                selectedTable === table ? 'ring-2 ring-[#003B7E] bg-blue-50' : 'hover:bg-gray-100'
              }`}
            >
              <p className="font-medium">{table}</p>
            </div>
          ))}
        </div>
      </div>

      {selectedTable && tableFields.length > 0 && (
        <TableFields
          tableName={selectedTable}
          fields={tableFields}
          loadingDescriptions={loadingDescriptions}
        />
      )}

      <div className="flex justify-end">
        <button
          onClick={onImport}
          disabled={loading}
          className="bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 flex items-center"
        >
          <Save className="h-4 w-4 mr-2" />
          Import to Dictionary
        </button>
      </div>
    </div>
  );
}