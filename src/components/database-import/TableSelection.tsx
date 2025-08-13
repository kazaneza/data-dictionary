import React, { useState, useMemo } from 'react';
import { Search, CheckSquare, Square, Database, Table2, Loader2 } from 'lucide-react';

interface TableSelectionProps {
  tables: string[];
  selectedTables: string[];
  onTableSelectionChange: (selectedTables: string[]) => void;
  loading?: boolean;
}

export default function TableSelection({
  tables,
  selectedTables,
  onTableSelectionChange,
  loading = false
}: TableSelectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectAll, setSelectAll] = useState(false);

  const filteredTables = useMemo(() => {
    if (!searchTerm) return tables;
    return tables.filter(table => 
      table.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [tables, searchTerm]);

  const handleSelectAll = () => {
    if (selectAll) {
      onTableSelectionChange([]);
      setSelectAll(false);
    } else {
      onTableSelectionChange(filteredTables);
      setSelectAll(true);
    }
  };

  const handleTableToggle = (tableName: string) => {
    const isSelected = selectedTables.includes(tableName);
    if (isSelected) {
      onTableSelectionChange(selectedTables.filter(t => t !== tableName));
    } else {
      onTableSelectionChange([...selectedTables, tableName]);
    }
  };

  const isTableSelected = (tableName: string) => selectedTables.includes(tableName);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[#003B7E]" />
        <span className="ml-2 text-gray-600">Loading tables...</span>
      </div>
    );
  }

  if (tables.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Database className="h-12 w-12 mx-auto mb-4 text-gray-300" />
        <p>No tables found in the database</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Table2 className="h-5 w-5 text-[#003B7E]" />
          <h3 className="font-medium">
            Select Tables ({selectedTables.length} of {tables.length} selected)
          </h3>
        </div>
        <div className="text-sm text-gray-500">
          {filteredTables.length !== tables.length && (
            <span>{filteredTables.length} filtered</span>
          )}
        </div>
      </div>

      {/* Search and Select All */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tables..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
          />
        </div>
        <button
          onClick={handleSelectAll}
          className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          {selectAll ? (
            <CheckSquare className="h-4 w-4 text-[#003B7E]" />
          ) : (
            <Square className="h-4 w-4 text-gray-400" />
          )}
          <span className="text-sm">
            {selectAll ? 'Deselect All' : 'Select All'}
          </span>
        </button>
      </div>

      {/* Table List */}
      <div className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
        {filteredTables.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            No tables match your search
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredTables.map((tableName) => (
              <div
                key={tableName}
                className={`flex items-center space-x-3 p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                  isTableSelected(tableName) ? 'bg-blue-50' : ''
                }`}
                onClick={() => handleTableToggle(tableName)}
              >
                <div className="flex-shrink-0">
                  {isTableSelected(tableName) ? (
                    <CheckSquare className="h-5 w-5 text-[#003B7E]" />
                  ) : (
                    <Square className="h-5 w-5 text-gray-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {tableName}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <Table2 className="h-4 w-4 text-gray-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selection Summary */}
      {selectedTables.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <CheckSquare className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-blue-800">
              {selectedTables.length} table{selectedTables.length !== 1 ? 's' : ''} selected for import
            </span>
          </div>
          {selectedTables.length <= 5 ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {selectedTables.map((tableName) => (
                <span
                  key={tableName}
                  className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                >
                  {tableName}
                </span>
              ))}
            </div>
          ) : (
            <div className="mt-2 text-xs text-blue-600">
              {selectedTables.slice(0, 3).join(', ')} and {selectedTables.length - 3} more...
            </div>
          )}
        </div>
      )}
    </div>
  );
}