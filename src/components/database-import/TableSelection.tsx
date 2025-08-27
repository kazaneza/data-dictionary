import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { Search, CheckSquare, Square, Database, Table2, Loader2 } from 'lucide-react';

// Virtual scrolling component for large lists
const VirtualizedTableList = React.memo(({ 
  items, 
  selectedTables, 
  onToggle, 
  itemHeight = 56,
  containerHeight = 384 
}: {
  items: string[];
  selectedTables: string[];
  onToggle: (tableName: string) => void;
  itemHeight?: number;
  containerHeight?: number;
}) => {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(startIndex + visibleCount + 5, items.length); // +5 for buffer
  const visibleItems = items.slice(startIndex, endIndex);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  return (
    <div 
      ref={containerRef}
      className="overflow-y-auto border border-gray-200 rounded-lg"
      style={{ height: containerHeight }}
      onScroll={handleScroll}
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${startIndex * itemHeight}px)` }}>
          {visibleItems.map((tableName, index) => {
            const actualIndex = startIndex + index;
            const isSelected = selectedTables.includes(tableName);
            
            return (
              <TableRow
                key={`${tableName}-${actualIndex}`}
                tableName={tableName}
                isSelected={isSelected}
                onToggle={onToggle}
                style={{ height: itemHeight }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
});

// Optimized table row component
const TableRow = React.memo(({ 
  tableName, 
  isSelected, 
  onToggle,
  style
}: { 
  tableName: string; 
  isSelected: boolean; 
  onToggle: (tableName: string) => void;
  style?: React.CSSProperties;
}) => {
  const handleClick = useCallback(() => {
    onToggle(tableName);
  }, [tableName, onToggle]);

  return (
    <div
      className={`flex items-center space-x-3 p-3 hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100 ${
        isSelected ? 'bg-blue-50' : ''
      }`}
      onClick={handleClick}
      style={style}
    >
      <div className="flex-shrink-0">
        {isSelected ? (
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
  );
});

// Web Worker for filtering (if available)
const createFilterWorker = () => {
  if (typeof Worker === 'undefined') return null;
  
  const workerCode = `
    self.onmessage = function(e) {
      const { tables, searchTerm, maxResults } = e.data;
      const searchLower = searchTerm.toLowerCase();
      const results = [];
      
      for (let i = 0; i < tables.length && results.length < maxResults; i++) {
        if (tables[i].toLowerCase().includes(searchLower)) {
          results.push(tables[i]);
        }
      }
      
      self.postMessage(results);
    };
  `;
  
  try {
    const blob = new Blob([workerCode], { type: 'application/javascript' });
    return new Worker(URL.createObjectURL(blob));
  } catch {
    return null;
  }
};

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
  const [filteredTables, setFilteredTables] = useState<string[]>(tables);
  const [isFiltering, setIsFiltering] = useState(false);
  const [inputValue, setInputValue] = useState('');
  
  const workerRef = useRef<Worker | null>(null);
  const filterTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const selectedTablesSetRef = useRef(new Set(selectedTables));
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Initialize worker
  useEffect(() => {
    workerRef.current = createFilterWorker();
    
    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
      }
    };
  }, []);

  // Update selected tables set when selectedTables changes
  useEffect(() => {
    selectedTablesSetRef.current = new Set(selectedTables);
  }, [selectedTables]);

  // Optimized filtering with Web Worker or chunked processing
  const performFilter = useCallback(async (searchValue: string, tableList: string[]) => {
    if (!searchValue.trim()) {
      setFilteredTables(tableList);
      setIsFiltering(false);
      return;
    }

    setIsFiltering(true);
    const maxResults = 1000; // Limit results for performance

    if (workerRef.current && tableList.length > 500) {
      // Use Web Worker for large datasets
      return new Promise<void>((resolve) => {
        const worker = workerRef.current!;
        
        const handleMessage = (e: MessageEvent) => {
          setFilteredTables(e.data);
          setIsFiltering(false);
          worker.removeEventListener('message', handleMessage);
          resolve();
        };
        
        worker.addEventListener('message', handleMessage);
        worker.postMessage({ tables: tableList, searchTerm: searchValue, maxResults });
      });
    } else {
      // Use chunked processing for smaller datasets or when Worker is not available
      return new Promise<void>((resolve) => {
        const searchLower = searchValue.toLowerCase();
        const results: string[] = [];
        let index = 0;
        const chunkSize = 100;

        const processChunk = () => {
          const endIndex = Math.min(index + chunkSize, tableList.length);
          
          for (let i = index; i < endIndex && results.length < maxResults; i++) {
            if (tableList[i].toLowerCase().includes(searchLower)) {
              results.push(tableList[i]);
            }
          }
          
          index = endIndex;
          
          if (index >= tableList.length || results.length >= maxResults) {
            setFilteredTables(results);
            setIsFiltering(false);
            resolve();
          } else {
            // Continue processing in next frame
            requestAnimationFrame(processChunk);
          }
        };
        
        requestAnimationFrame(processChunk);
      });
    }
  }, []);

  // Debounced search with immediate clear
  useEffect(() => {
    if (filterTimeoutRef.current) {
      clearTimeout(filterTimeoutRef.current);
    }

    if (!inputValue.trim()) {
      // Immediate update for empty search
      setSearchTerm('');
      setFilteredTables(tables);
      setIsFiltering(false);
      return;
    }

    setIsFiltering(true);
    filterTimeoutRef.current = setTimeout(() => {
      setSearchTerm(inputValue);
      performFilter(inputValue, tables);
    }, 300);

    return () => {
      if (filterTimeoutRef.current) {
        clearTimeout(filterTimeoutRef.current);
      }
    };
  }, [inputValue, tables, performFilter]);

  // Update filtered tables when tables change
  useEffect(() => {
    if (!inputValue.trim()) {
      setFilteredTables(tables);
    } else {
      performFilter(inputValue, tables);
    }
  }, [tables, inputValue, performFilter]);

  // Memoized selection state calculations using Set for O(1) lookups
  const selectionState = useMemo(() => {
    const selectedSet = selectedTablesSetRef.current;
    let filteredSelectedCount = 0;
    
    for (const table of filteredTables) {
      if (selectedSet.has(table)) {
        filteredSelectedCount++;
      }
    }
    
    const allFilteredSelected = filteredSelectedCount === filteredTables.length && filteredTables.length > 0;
    const someFilteredSelected = filteredSelectedCount > 0;
    
    return {
      allSelected: allFilteredSelected,
      someSelected: someFilteredSelected,
      selectedCount: filteredSelectedCount
    };
  }, [filteredTables, selectedTables]);

  const handleSelectAll = useCallback(() => {
    if (selectionState.allSelected) {
      // Deselect all filtered tables using Set for performance
      const filteredSet = new Set(filteredTables);
      const remainingSelected = selectedTables.filter(table => !filteredSet.has(table));
      onTableSelectionChange(remainingSelected);
    } else {
      // Select all filtered tables using Set to avoid duplicates
      const newSelectionSet = new Set([...selectedTables, ...filteredTables]);
      onTableSelectionChange(Array.from(newSelectionSet));
    }
  }, [filteredTables, selectedTables, onTableSelectionChange, selectionState.allSelected]);

  const handleTableToggle = useCallback((tableName: string) => {
    const selectedSet = selectedTablesSetRef.current;
    const isSelected = selectedSet.has(tableName);
    
    if (isSelected) {
      onTableSelectionChange(selectedTables.filter(t => t !== tableName));
    } else {
      onTableSelectionChange([...selectedTables, tableName]);
    }
  }, [selectedTables, onTableSelectionChange]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);
  }, []);

  const clearSearch = useCallback(() => {
    setInputValue('');
    setSearchTerm('');
    setFilteredTables(tables);
    setIsFiltering(false);
    if (searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [tables]);

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
          {isFiltering && <span className="text-blue-600">Filtering...</span>}
          {!isFiltering && searchTerm && filteredTables.length !== tables.length && (
            <span>{filteredTables.length} filtered</span>
          )}
        </div>
      </div>

      {/* Search and Select All */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={inputValue}
            onChange={handleSearchChange}
            placeholder="Search tables..."
            className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
            autoComplete="off"
          />
          {inputValue && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>
        <button
          onClick={handleSelectAll}
          disabled={isFiltering || filteredTables.length === 0}
          className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {selectionState.allSelected ? (
            <CheckSquare className="h-4 w-4 text-[#003B7E]" />
          ) : (
            <Square className={`h-4 w-4 ${selectionState.someSelected ? 'text-[#003B7E]' : 'text-gray-400'}`} />
          )}
          <span className="text-sm">
            {selectionState.allSelected ? 'Deselect All' : 'Select All'}
            {inputValue && ` (${filteredTables.length})`}
          </span>
        </button>
      </div>

      {/* Virtualized Table List */}
      {isFiltering ? (
        <div className="flex items-center justify-center py-8 border border-gray-200 rounded-lg">
          <Loader2 className="h-6 w-6 animate-spin text-[#003B7E] mr-2" />
          <span className="text-gray-600">Filtering tables...</span>
        </div>
      ) : filteredTables.length === 0 ? (
        <div className="p-4 text-center text-gray-500 border border-gray-200 rounded-lg">
          {inputValue ? 'No tables match your search' : 'No tables available'}
        </div>
      ) : (
        <VirtualizedTableList
          items={filteredTables}
          selectedTables={selectedTables}
          onToggle={handleTableToggle}
          containerHeight={384}
          itemHeight={56}
        />
      )}

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
              {selectedTables.slice(0, 3).join(', ')} and {selectedTables.length - 3} more
            </div>
          )}
        </div>
      )}
    </div>
  );
}