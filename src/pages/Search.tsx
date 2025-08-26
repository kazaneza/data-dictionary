import React, { useState, useEffect } from 'react';
import { 
  Search as SearchIcon, 
  Loader2, 
  Database, 
  Table2, 
  ArrowRight,
  Sparkles,
  History,
  X,
  Filter,
  Command,
  BookOpen,
  Lightbulb
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import * as api from '../lib/api';
import { Link } from 'react-router-dom';

// Custom hook for debounced values
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Custom hook for debounced values
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Custom hook for debounced values
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Custom hook for debounced values
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

interface SearchResult {
  type: 'table' | 'field';
  name: string;
  description: string;
  tableName?: string;
  databaseName: string;
  sourceName: string;
  dataType?: string;
  id: string;
  score: number;
}

interface SearchFilters {
  type: string;
  minScore: number;
  source: string;
  database: string;
}

const searchExamples = [
  "Find all customer-related tables",
  "Show me transaction fields",
  "Tables containing user information",
  "Fields related to payments",
  "Find audit log tables"
];

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    type: 'all',
    minScore: 0.7,
    source: '',
    database: ''
  });
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [availableFilters, setAvailableFilters] = useState<{
    sources: string[];
    databases: string[];
    categories: string[];
  }>({
    sources: [],
    databases: [],
    categories: []
  });
  
  // Debounce the search query to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 500);
  
  // Track current search request to cancel if needed
  const [currentSearchController, setCurrentSearchController] = useState<AbortController | null>(null);
  
  // Debounce the search query to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 500);
  
  // Track current search request to cancel if needed
  const [currentSearchController, setCurrentSearchController] = useState<AbortController | null>(null);
  
  // Debounce the search query to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 500);
  
  // Track current search request to cancel if needed
  const [currentSearchController, setCurrentSearchController] = useState<AbortController | null>(null);
  
  // Debounce the search query to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 500);
  
  // Track current search request to cancel if needed
  const [currentSearchController, setCurrentSearchController] = useState<AbortController | null>(null);

  useEffect(() => {
    const history = localStorage.getItem('searchHistory');
    if (history) {
      setSearchHistory(JSON.parse(history));
    }

    // Load available filters only when filters panel is opened
    const loadFilters = async () => {
      if (filtersLoaded) return;
      
      try {
        const response = await fetch('http://10.24.37.99:8000/api/search/filters', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setAvailableFilters(data);
          setFiltersLoaded(true);
        }
      } catch (error) {
        console.error('Failed to load filters:', error);
        setFiltersLoaded(true);
      }
    };

    // Only load filters when filters panel is shown
    if (showFilters && !filtersLoaded) {
      loadFilters();
    }

    const loadFilters = async () => {
      try {
        const response = await fetch('http://10.24.37.99:8000/api/search/filters', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setAvailableFilters(data);
        }
      } catch (error) {
        console.error('Failed to load filters:', error);
      }
    };
    loadFilters();

    // Add keyboard shortcut for command palette
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(true);
      }
      if (e.key === 'Escape') {
        setShowCommandPalette(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showFilters, filtersLoaded]);

  // Update displayed results when results change
  useEffect(() => {
    if (results.length === 0) {
      setDisplayedResults([]);
      setShowLoadMore(false);
    } else {
      const initial = results.slice(0, INITIAL_RESULTS_COUNT);
      setDisplayedResults(initial);
      setShowLoadMore(results.length > INITIAL_RESULTS_COUNT);
    }
  }, [results]);

  // Effect to handle debounced search
  useEffect(() => {
    if (debouncedQuery.trim() && debouncedQuery.length >= 2) {
      performSearch(debouncedQuery);
    } else {
      // Clear results immediately when query is empty
      setResults([]);
      setDisplayedResults([]);
      setError(null);
      setShowLoadMore(false);
      // Cancel any ongoing search
      if (currentSearchController) {
        currentSearchController.abort();
        setCurrentSearchController(null);
      }
      setLoading(false);
    }
  }, [debouncedQuery, filters]);

  const saveToHistory = (query: string) => {
    const updatedHistory = [query, ...searchHistory.filter(q => q !== query)].slice(0, 5);
    setSearchHistory(updatedHistory);
    localStorage.setItem('searchHistory', JSON.stringify(updatedHistory));
  };

  const performSearch = async (searchQuery: string) => {
    // Don't search if query is too short
    if (searchQuery.trim().length < 2) {
      return;
    }

    // Cancel previous search if still running
    if (currentSearchController) {
      currentSearchController.abort();
    }

    // Create new abort controller for this search
    const controller = new AbortController();
    setCurrentSearchController(controller);

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://10.24.37.99:8000/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        signal: controller.signal,
        body: JSON.stringify({
          query: searchQuery,
          type_filter: filters.type === 'all' ? null : filters.type,
          source_filter: filters.source || null,
          database_filter: filters.database || null,
          min_score: filters.minScore
        })
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      // Limit results to prevent UI freezing
      const limitedResults = data.results.slice(0, 100);
      setResults(limitedResults);
      saveToHistory(searchQuery);
      setShowCommandPalette(false);
    } catch (error: any) {
      // Don't show error if request was aborted (user typed new query)
      if (error.name === 'AbortError') {
        return;
      }
      console.error('Search error:', error);
      setError('Failed to perform search');
      toast.error('Search failed. Please try again.');
    } finally {
      setLoading(false);
      setCurrentSearchController(null);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      setDisplayedResults([]);
      setError(null);
      setShowLoadMore(false);
      if (query.trim().length < 2 && query.trim().length > 0) {
        toast.error('Please enter at least 2 characters to search');
      }
      return;
    }

    // For manual search (form submit), search immediately without debounce
    performSearch(query);
  };

  const handleQueryChange = (newQuery: string) => {
    setQuery(newQuery);
    
    // If query is empty, clear results immediately
    if (!newQuery.trim()) {
      setResults([]);
      setDisplayedResults([]);
      setError(null);
      setShowLoadMore(false);
      if (currentSearchController) {
        currentSearchController.abort();
        setCurrentSearchController(null);
      }
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setDisplayedResults([]);
    setError(null);
    setShowLoadMore(false);
    if (currentSearchController) {
      currentSearchController.abort();
      setCurrentSearchController(null);
    }
    setLoading(false);
  };

  const loadMoreResults = () => {
    const currentCount = displayedResults.length;
    const nextBatch = results.slice(currentCount, currentCount + LOAD_MORE_COUNT);
    setDisplayedResults([...displayedResults, ...nextBatch]);
    setShowLoadMore(currentCount + LOAD_MORE_COUNT < results.length);
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
    // Perform search immediately for examples
    performSearch(example);
  };

  const handleHistoryClick = (historyQuery: string) => {
    setQuery(historyQuery);
    // Perform search immediately for history items
    performSearch(historyQuery);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentSearchController) {
        currentSearchController.abort();
      }
    };
  }, []);

  // Handle filter changes with debounce
  const handleFilterChange = (newFilters: SearchFilters) => {
    setFilters(newFilters);
    // The useEffect will handle the search with debounced query
  };

  // Memoize search results to prevent unnecessary re-renders
  const memoizedResults = React.useMemo(() => {
    return results.slice(0, 20); // Limit to first 20 results for performance
  }, [results]);

  return (
    <div className="min-h-[calc(100vh-5rem)] flex flex-col bg-gradient-to-b from-gray-50 to-white">
      {/* Command Palette */}
      {showCommandPalette && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-[20vh] z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="p-4 border-b">
              <div className="flex items-center space-x-2">
                <Command className="h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => handleQueryChange(e.target.value)}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent border-none outline-none text-lg"
                  autoFocus
                />
                <kbd className="px-2 py-1 text-xs bg-gray-100 rounded-md">ESC</kbd>
              </div>
            </div>
            <div className="p-2">
              <div className="px-2 py-1 text-xs font-medium text-gray-500">
                Quick Actions
              </div>
              <button
                onClick={() => {
                  handleSearch();
                  setShowCommandPalette(false);
                }}
                className="w-full px-2 py-2 flex items-center space-x-2 hover:bg-gray-100 rounded-lg"
              >
                <SearchIcon className="h-4 w-4 text-gray-400" />
                <span>Search Data Dictionary</span>
              </button>
              <button
                onClick={() => {
                  setShowFilters(true);
                  setShowCommandPalette(false);
                }}
                className="w-full px-2 py-2 flex items-center space-x-2 hover:bg-gray-100 rounded-lg"
              >
                <Filter className="h-4 w-4 text-gray-400" />
                <span>Show Search Filters</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Header */}
      <div className="flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-[#003B7E]/5 to-transparent pointer-events-none" />
        
        <div className="relative max-w-4xl w-full">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center justify-center">
            Data Dictionary Search
            <Sparkles className="h-8 w-8 ml-2 text-[#003B7E]" />
          </h1>
          <p className="text-lg text-gray-600 text-center mb-8">
            Search across tables, fields, and descriptions using natural language
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="w-full">
            <div className="relative group">
              <div className="absolute inset-0 bg-[#003B7E] rounded-xl opacity-5 group-hover:opacity-10 transition-opacity" />
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => handleQueryChange(e.target.value)}
                  placeholder="Try 'Find tables containing customer information' or 'Show me fields related to transactions'"
                  className="w-full px-4 py-4 pl-12 pr-32 text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#003B7E] focus:border-transparent bg-white shadow-sm"
                />
                <SearchIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
                  {query && (
                    <button
                      type="button"
                      onClick={clearSearch}
                      className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                    >
                      <X className="h-5 w-5 text-gray-400" />
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {loading ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <>
                        <SearchIcon className="h-4 w-4" />
                        <span>Search</span>
                      </>
                    )}
                  </button>
                </div>
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to perform search');
      toast.error('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
  return (
    <div className="min-h-[calc(100vh-5rem)] flex flex-col bg-gradient-to-b from-gray-50 to-white">
      {/* Command Palette */}
      {showCommandPalette && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-[20vh] z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="p-4 border-b">
              <div className="flex items-center space-x-2">
                <Command className="h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent border-none outline-none text-lg"
                  autoFocus
                />
                <kbd className="px-2 py-1 text-xs bg-gray-100 rounded-md">ESC</kbd>
              </div>
            </div>
            <div className="p-2">
              <div className="px-2 py-1 text-xs font-medium text-gray-500">
                Quick Actions
              </div>
              <button
                onClick={() => {
                  handleSearch();
                  setShowCommandPalette(false);
                }}
                className="w-full px-2 py-2 flex items-center space-x-2 hover:bg-gray-100 rounded-lg"
              >
                <SearchIcon className="h-4 w-4 text-gray-400" />
                <span>Search Data Dictionary</span>
              </button>
              <button
                onClick={() => {
                  setShowFilters(true);
                  setShowCommandPalette(false);
                }}
                className="w-full px-2 py-2 flex items-center space-x-2 hover:bg-gray-100 rounded-lg"
              >
                <Filter className="h-4 w-4 text-gray-400" />
                <span>Show Search Filters</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Header */}
      <div className="flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-[#003B7E]/5 to-transparent pointer-events-none" />
        
        <div className="relative max-w-4xl w-full">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center justify-center">
            Data Dictionary Search
            <Sparkles className="h-8 w-8 ml-2 text-[#003B7E]" />
          </h1>
          <p className="text-lg text-gray-600 text-center mb-8">
            Search across tables, fields, and descriptions using natural language
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="w-full">
            <div className="relative group">
              <div className="absolute inset-0 bg-[#003B7E] rounded-xl opacity-5 group-hover:opacity-10 transition-opacity" />
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Try 'Find tables containing customer information' or 'Show me fields related to transactions'"
                  className="w-full px-4 py-4 pl-12 pr-32 text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#003B7E] focus:border-transparent bg-white shadow-sm"
                />
                <SearchIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
                  {query && (
                    <button
                      type="button"
                      onClick={clearSearch}
                      className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                    >
                      <X className="h-5 w-5 text-gray-400" />
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {loading ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <>
                        <SearchIcon className="h-4 w-4" />
                        <span>Search</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Search History and Examples */}
            <div className="mt-4 flex flex-col space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  {searchHistory.length > 0 && (
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <History className="h-4 w-4" />
                      <span>Recent:</span>
                      {searchHistory.map((historyQuery, index) => (
                        <button
                          key={index}
                          onClick={() => setQuery(historyQuery)}
                          className="text-[#003B7E] hover:underline truncate max-w-xs"
                        >
                          {historyQuery}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                
                <button
                  type="button"
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center space-x-1 text-sm text-gray-600 hover:text-[#003B7E]"
                >
                  <Filter className="h-4 w-4" />
                  <span>Filters</span>
                </button>
              </div>

              {/* Search Examples */}
              {!query && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {searchExamples.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => setQuery(example)}
                    className="text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-[#003B7E]/20 hover:bg-[#003B7E]/5 transition-colors group"
                  >
                    <div className="flex items-center space-x-2">
                      <Lightbulb className="h-4 w-4 text-gray-400 group-hover:text-[#003B7E]" />
                      <span className="text-sm text-gray-600 group-hover:text-[#003B7E]">
                        {example}
                      </span>
                    </div>
                  </button>
                ))}
                </div>
              )}
            </div>

            {/* Filters Panel */}
            {showFilters && (
              <div className="mt-4 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
                {!filtersLoaded && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-[#003B7E] mr-2" />
                    <span className="text-sm text-gray-600">Loading filters...</span>
                  </div>
                )}
                {filtersLoaded && (
                {!filtersLoaded && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-[#003B7E] mr-2" />
                    <span className="text-sm text-gray-600">Loading filters...</span>
                  </div>
                )}
                {filtersLoaded && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Result Type
                    </label>
                    <select
                      value={filters.type}
                      onChange={(e) => setFilters({ ...filters, type: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="all">All Results</option>
                      <option value="table">Tables Only</option>
                      <option value="field">Fields Only</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Source System
                    </label>
                    <select
                      value={filters.source}
                      onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="">All Sources</option>
                      {availableFilters.sources.map((source) => (
                        <option key={source} value={source}>
                          {source}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Database
                    </label>
                    <select
                      value={filters.database}
                      onChange={(e) => setFilters({ ...filters, database: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    >
                      <option value="">All Databases</option>
                      {availableFilters.databases.map((database) => (
                        <option key={database} value={database}>
                          {database}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Minimum Match Score
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={filters.minScore}
                        onChange={(e) => setFilters({ ...filters, minScore: parseFloat(e.target.value) })}
                        className="flex-1"
                      />
                      <span className="text-sm bg-[#003B7E]/10 text-[#003B7E] px-2 py-1 rounded-full min-w-[4rem] text-center">
                        {Math.round(filters.minScore * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
                )}
                )}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Search Results */}
      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {query.trim() && query.trim().length < 2 && (
            <div className="text-center py-8">
              <div className="inline-block p-4 rounded-full bg-yellow-100 mb-4">
                <SearchIcon className="h-6 w-6 text-yellow-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900">
                Keep typing...
              </h3>
              <p className="mt-1 text-gray-500">
                Enter at least 2 characters to start searching
              </p>
            </div>
          )}
          {error ? (
            <div className="text-center text-red-600 bg-red-50 p-4 rounded-lg">
              {error}
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#003B7E] mr-3" />
              <span className="text-gray-600">Searching...</span>
            </div>
          ) : displayedResults.length > 0 ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  Search Results
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    (showing {displayedResults.length} of {results.length} matches)
                  </span>
                </h2>
                <button
                  onClick={clearSearch}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear Results
                </button>
              </div>
              
              <div className="grid grid-cols-1 gap-4">
                {displayedResults.map((result) => (
                  <div
                    key={result.id}
                    className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-all duration-200 border border-gray-100"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-lg ${
                          result.type === 'table' 
                            ? 'bg-blue-50 text-blue-600' 
                            : 'bg-purple-50 text-purple-600'
                        }`}>
                          {result.type === 'table' ? (
                            <Database className="h-5 w-5" />
                          ) : (
                            <Table2 className="h-5 w-5" />
                          )}
                        </div>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">
                            {result.name}
                          </h3>
                          <p className="text-sm text-gray-500">
                            {result.type === 'field' && result.tableName
                              ? `Field in ${result.tableName}`
                              : `Table in ${result.databaseName}`}
                          </p>
                        </div>
                      </div>
                      <Link
                        to={`/dictionary`}
                        className="flex items-center text-[#003B7E] hover:text-[#002c5f] text-sm group"
                      >
                        <BookOpen className="h-4 w-4 mr-1" />
                        View Details
                        <ArrowRight className="h-4 w-4 ml-1 transform group-hover:translate-x-1 transition-transform" />
                      </Link>
                    </div>
                    
                    <p className="mt-2 text-gray-600">{result.description}</p>
                    
                    <div className="mt-4 flex items-center space-x-2">
                      <div className="flex-1 flex items-center space-x-2 text-sm text-gray-500">
                        <span className="px-2 py-1 bg-gray-100 rounded-full">
                          {result.sourceName}
                        </span>
                        <span>•</span>
                        <span className="px-2 py-1 bg-gray-100 rounded-full">
                          {result.databaseName}
                        </span>
                        {result.type === 'field' && result.dataType && (
                          <>
                            <span>•</span>
                            <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded-full">
                              {result.dataType}
                            </span>
                          </>
                        )}
                      </div>
                      <div className="text-sm">
                        <span className="px-2 py-1 bg-green-50 text-green-700 rounded-full">
                          {Math.round(result.score * 100)}% match
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Load More Button */}
              {showLoadMore && (
                <div className="flex justify-center mt-8">
                  <button
                    onClick={loadMoreResults}
                    className="bg-[#003B7E] text-white px-6 py-2 rounded-lg hover:bg-[#002c5f] transition-colors flex items-center space-x-2"
                  >
                    <span>Load More Results</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          ) : debouncedQuery && debouncedQuery.length >= 2 && !loading ? (
            <div className="text-center py-12">
              <div className="inline-block p-4 rounded-full bg-gray-100 mb-4">
                <SearchIcon className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900">
                No results found
              </h3>
              <p className="mt-1 text-gray-500">
                Try adjusting your search terms or filters
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}