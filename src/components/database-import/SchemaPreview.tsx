import React from 'react';
import { Save, ArrowRight } from 'lucide-react';
import { SourceSystem } from '../../lib/api';
import TableFields from './TableFields';
import TableSelection from './TableSelection';

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
  selectedTables: string[];
  tableFields: any[];
  loading: boolean;
  loadingDescriptions: boolean;
  onTableSelect: (table: string) => void;
  onTableSelectionChange: (selectedTables: string[]) => void;
  onImport: () => void;
}

export default function SchemaPreview({
  previewData,
  config,
  sources,
  selectedTable,
  selectedTables,
  tableFields,
  loading,
  loadingDescriptions,
  onTableSelect,
  onTableSelectionChange,
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

      {/* Table Selection */}
      <TableSelection
        tables={previewData.tables}
        selectedTables={selectedTables}
        onTableSelectionChange={onTableSelectionChange}
        loading={loading}
      />

      {/* Preview Selected Table */}
      {selectedTables.length > 0 && (
        <div className="border-t pt-6">
          <h3 className="font-medium mb-4">Preview Table Schema</h3>
          <div className="grid grid-cols-4 gap-2 mb-4">
            {selectedTables.slice(0, 8).map((table) => (
              <button
                key={table}
                onClick={() => onTableSelect(table)}
                className={`p-2 text-sm rounded-lg transition-colors ${
                  selectedTable === table 
                    ? 'bg-[#003B7E] text-white' 
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {table}
              </button>
            ))}
            {selectedTables.length > 8 && (
              <div className="p-2 text-sm text-gray-500 bg-gray-50 rounded-lg flex items-center justify-center">
                +{selectedTables.length - 8} more
              </div>
            )}
          </div>
        </div>
      )}

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
          disabled={loading || selectedTables.length === 0}
          className="bg-[#003B7E] text-white px-6 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 flex items-center space-x-2"
        >
          <Save className="h-4 w-4 mr-2" />
          <span>Import {selectedTables.length} Table{selectedTables.length !== 1 ? 's' : ''}</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}