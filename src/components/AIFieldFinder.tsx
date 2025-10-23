import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Loader2,
  Sparkles,
  Table2,
  AlertCircle,
  CheckCircle,
  Filter,
  X,
  Key,
  Info,
} from 'lucide-react';
import { toast } from 'react-hot-toast';

interface FieldMatch {
  id: string;
  name: string;
  description: string;
  tableName: string;
  databaseName: string;
  sourceName: string;
  dataType: string;
  score: number;
  reason: string;
  metadata_confidence?: string;
  is_primary_key?: boolean;
  is_nullable?: boolean;
}

interface AIFieldFinderResponse {
  query: string;
  interpretation: string;
  total: number;
  results: FieldMatch[];
}

export default function AIFieldFinder() {
  const [query, setQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState<FieldMatch[]>([]);
  const [interpretation, setInterpretation] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [sourceFilter, setSourceFilter] = useState('');
  const [databaseFilter, setDatabaseFilter] = useState('');
  const [availableFilters, setAvailableFilters] = useState<{
    sources: string[];
    databases: string[];
  }>({ sources: [], databases: [] });

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setQuery(transcript);
        setIsListening(false);
        toast.success('Voice input captured');
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        toast.error('Voice input failed. Please try again.');
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    loadFilters();

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const loadFilters = async () => {
    try {
      const response = await fetch('http://10.24.37.99:8000/api/search/filters', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableFilters({
          sources: data.sources || [],
          databases: data.databases || []
        });
      }
    } catch (error) {
      console.error('Failed to load filters:', error);
    }
  };

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      toast.error('Voice input is not supported in this browser');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
        toast.success('Listening... Speak now');
      } catch (error) {
        console.error('Failed to start voice recognition:', error);
        toast.error('Failed to start voice input');
      }
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    if (!query.trim()) {
      toast.error('Please enter a description or use voice input');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResults([]);
    setInterpretation('');

    try {
      const response = await fetch('http://10.24.37.99:8000/api/search/natural-language-fields', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({
          query: query,
          source_filter: sourceFilter || null,
          database_filter: databaseFilter || null,
          limit: 20
        })
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data: AIFieldFinderResponse = await response.json();
      setResults(data.results);
      setInterpretation(data.interpretation);

      if (data.results.length === 0) {
        toast('No matching fields found. Try a different description.', { icon: '🔍' });
      } else {
        toast.success(`Found ${data.results.length} matching fields`);
      }
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to search for fields. Please try again.');
      toast.error('Search failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setInterpretation('');
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <Sparkles className="h-10 w-10 text-[#003B7E] mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">
              AI Field Finder
            </h1>
          </div>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Describe what kind of field you're looking for in plain English, or use voice input.
            Our AI will find the most relevant database fields.
          </p>
        </div>

        <form onSubmit={handleSearch} className="mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-1 relative">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Example: I need a field for storing customer legal documents..."
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003B7E] focus:border-transparent resize-none"
                />
                {query && (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="absolute top-2 right-2 p-1 hover:bg-gray-100 rounded-full"
                  >
                    <X className="h-5 w-5 text-gray-400" />
                  </button>
                )}
              </div>
              <button
                type="button"
                onClick={toggleVoiceInput}
                disabled={isProcessing}
                className={`p-4 rounded-lg transition-all duration-200 ${
                  isListening
                    ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
                title={isListening ? 'Stop listening' : 'Start voice input'}
              >
                {isListening ? (
                  <MicOff className="h-6 w-6" />
                ) : (
                  <Mic className="h-6 w-6" />
                )}
              </button>
            </div>

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center space-x-2 text-sm text-gray-600 hover:text-[#003B7E]"
              >
                <Filter className="h-4 w-4" />
                <span>Filters</span>
              </button>

              <button
                type="submit"
                disabled={isProcessing || !query.trim()}
                className="bg-[#003B7E] text-white px-6 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    <span>Find Fields</span>
                  </>
                )}
              </button>
            </div>

            {showFilters && (
              <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source System
                  </label>
                  <select
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
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
                    value={databaseFilter}
                    onChange={(e) => setDatabaseFilter(e.target.value)}
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
              </div>
            )}
          </div>
        </form>

        {interpretation && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-start space-x-3">
              <Sparkles className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-blue-900 mb-1">AI Interpretation</h3>
                <p className="text-blue-700">{interpretation}</p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-900 mb-1">Error</h3>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Matching Fields ({results.length})
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {results.map((field) => (
                <div
                  key={field.id}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
                        <Table2 className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {field.name}
                        </h3>
                        <p className="text-sm text-gray-500">
                          in {field.tableName}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm font-medium">
                        {Math.round(field.score * 100)}% match
                      </span>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                  </div>

                  <p className="text-gray-700 mb-3">{field.description}</p>

                  <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-3">
                    <p className="text-sm text-blue-900">
                      <span className="font-medium">Why it matches:</span> {field.reason}
                    </p>
                  </div>

                  <div className="flex items-center flex-wrap gap-2 text-sm text-gray-500">
                    <span className="px-2 py-1 bg-gray-100 rounded-full">
                      {field.sourceName}
                    </span>
                    <span>•</span>
                    <span className="px-2 py-1 bg-gray-100 rounded-full">
                      {field.databaseName}
                    </span>
                    <span>•</span>
                    <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded-full">
                      {field.dataType}
                    </span>
                    {field.is_primary_key && (
                      <>
                        <span>•</span>
                        <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded-full flex items-center gap-1">
                          <Key className="h-3 w-3" />
                          Primary Key
                        </span>
                      </>
                    )}
                    {field.metadata_confidence && (
                      <>
                        <span>•</span>
                        <span className={`px-2 py-1 rounded-full flex items-center gap-1 ${
                          field.metadata_confidence === 'high'
                            ? 'bg-green-50 text-green-700'
                            : field.metadata_confidence === 'medium'
                            ? 'bg-yellow-50 text-yellow-700'
                            : 'bg-gray-50 text-gray-600'
                        }`}>
                          <Info className="h-3 w-3" />
                          {field.metadata_confidence === 'high'
                            ? 'Well Documented'
                            : field.metadata_confidence === 'medium'
                            ? 'Partial Docs'
                            : 'Limited Docs'}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!isProcessing && !results.length && !error && query && (
          <div className="text-center py-12">
            <div className="inline-block p-4 bg-gray-100 rounded-full mb-4">
              <Sparkles className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900">
              Ready to search
            </h3>
            <p className="text-gray-500 mt-1">
              Click "Find Fields" to start your AI-powered search
            </p>
          </div>
        )}

        {!query && !isProcessing && (
          <div className="bg-gradient-to-br from-[#003B7E]/5 to-blue-50 rounded-xl p-8 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              How to use AI Field Finder
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="w-10 h-10 bg-[#003B7E] text-white rounded-lg flex items-center justify-center mb-3 font-bold">
                  1
                </div>
                <h4 className="font-medium text-gray-900 mb-2">Describe Your Need</h4>
                <p className="text-sm text-gray-600">
                  Type or speak what kind of field you're looking for in natural language
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="w-10 h-10 bg-[#003B7E] text-white rounded-lg flex items-center justify-center mb-3 font-bold">
                  2
                </div>
                <h4 className="font-medium text-gray-900 mb-2">AI Analysis</h4>
                <p className="text-sm text-gray-600">
                  Our AI interprets your request and searches through all database fields
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="w-10 h-10 bg-[#003B7E] text-white rounded-lg flex items-center justify-center mb-3 font-bold">
                  3
                </div>
                <h4 className="font-medium text-gray-900 mb-2">Get Results</h4>
                <p className="text-sm text-gray-600">
                  View ranked results with explanations of why each field matches
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
