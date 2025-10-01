import React, { useState, useEffect, useMemo } from 'react';
import { 
  Building2, FileSpreadsheet, Search, Database, Table2, Download, 
  Server, HardDrive, Filter, Loader2 
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { toast } from 'react-hot-toast';
import * as api from '../lib/api';

interface SourceType {
  id: string;
  name: string;
  description: string;
  category: string;
  databases: DatabaseType[];
}

interface DatabaseType {
  id: string;
  source_id: string;
  name: string;
  description: string;
  type: string;
  platform: string;
  location?: string;
  version?: string;
  tables: TableType[];
  totalTables: number;
}

interface TableType {
  id: string;
  database_id: string;
  category_id?: string;
  name: string;
  description: string;
  totalFields: number;
  fields: FieldType[];
  record_count?: number;
  last_imported?: string;
}

interface FieldType {
  id: string;
  table_id: string;
  name: string;
  type: string;
  description: string;
  nullable: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  default_value?: string;
  referenced_table?: string;
  referenced_column?: string;
}

interface CategoryType {
  id: string;
  name: string;
  description: string;
}

function DataDictionary() {
  const [sourceSystems, setSourceSystems] = useState<SourceType[]>([]);
  const [selectedSystems, setSelectedSystems] = useState<string[]>([]);
  const [selectedDatabases, setSelectedDatabases] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'systems' | 'databases' | 'tables' | 'fields'>('systems');
  const [filters, setFilters] = useState({
    platform: '',
    dbType: '',
  });

  const [sourceSearchTerm, setSourceSearchTerm] = useState<string>('');
  const [sourceCategory, setSourceCategory] = useState<string>('');

  const [sources, setSources] = useState<api.SourceSystem[]>([]);
  const [databases, setDatabases] = useState<api.Database[]>([]);
  const [tables, setTables] = useState<api.Table[]>([]);
  const [fields, setFields] = useState<api.Field[]>([]);
  const [categories, setCategories] = useState<api.Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [loadingFields, setLoadingFields] = useState(false);
  const [loadingTables, setLoadingTables] = useState(false);
  const [loadingDatabases, setLoadingDatabases] = useState(false);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch source systems & categories
        const [sourcesData, categoriesData] = await Promise.all([
          api.fetchSources(),
          api.fetchCategories()
        ]);

        setSources(sourcesData);
        setCategories(categoriesData);

        // Transform the source data to match local shape, 
        // with each database initialized with totalTables = 0:
        const transformedSources = sourcesData.map(source => ({
          ...source,
          databases: []
        }));
        setSourceSystems(transformedSources);

        // Fetch databases
        setLoadingDatabases(true);
        const databasesData = await api.fetchDatabases(1, 500); // Increased limit to see more databases
        setDatabases(databasesData);

        // Attach databases to sources, each with totalTables = 0
        const updatedSources = transformedSources.map(source => {
          const sourceDBs = databasesData.filter(db => db.source_id === source.id);
          return {
            ...source,
            databases: sourceDBs.map(db => ({
              ...db,
              tables: [],
              totalTables: 0, // Initialize to 0 so it's never undefined
            }))
          };
        });

        setSourceSystems(updatedSources);
        
        // Clear cache to ensure fresh data
        api.invalidateCache();
      } catch (error) {
        console.error('Error loading initial data:', error);
        setError('Failed to load data. Please try again later.');
        toast.error('Failed to load data');
      } finally {
        setLoading(false);
        setLoadingDatabases(false);
      }
    };

    loadInitialData();
  }, []);

  useEffect(() => {
    const loadTables = async () => {
      if (!selectedDatabases.length) return;

      try {
        setLoadingTables(true);
        const tablesPromises = selectedDatabases.map(dbId => api.fetchTables(dbId));
        const tablesResults = await Promise.all(tablesPromises);
        const allTables = tablesResults.flat();
        
        setTables(allTables);

        // Update each DB in each source to store tables + set totalTables
        setSourceSystems(prev =>
          prev.map(source => ({
            ...source,
            databases: source.databases.map(db => {
              const relevantTables = allTables.filter(t => t.database_id === db.id);
              return {
                ...db,
                totalTables: relevantTables.length,
                tables: relevantTables
              };
            })
          }))
        );
      } catch (error) {
        console.error('Error loading tables:', error);
        toast.error('Failed to load tables');
      } finally {
        setLoadingTables(false);
      }
    };

    loadTables();
  }, [selectedDatabases]);

  useEffect(() => {
    const loadFields = async () => {
      if (!selectedTable) return;
      try {
        setLoadingFields(true);
        const fieldsData = await api.fetchFields(selectedTable); // selectedTable should be the table's ID
        setFields(fieldsData);
      } catch (error) {
        console.error('Error loading fields:', error);
        toast.error('Failed to load fields');
      } finally {
        setLoadingFields(false);
      }
    };
    loadFields();
  }, [selectedTable]);

  // -- Filtering logic --
  const filteredSystems = useMemo(() => {
    let systems = [...sourceSystems];

    if (sourceCategory) {
      const selectedCategoryObj = categories.find(cat => cat.id === sourceCategory);
      if (selectedCategoryObj) {
        systems = systems.filter(sys => {
          // Find tables from sys's databases that belong to that category
          const systemTables = sys.databases.flatMap(db => 
            tables.filter(t => t.database_id === db.id)
          );
          return systemTables.some(t => t.category_id === selectedCategoryObj.id);
        });
      }
    }

    if (sourceSearchTerm) {
      systems = systems.filter(sys =>
        sys.name.toLowerCase().includes(sourceSearchTerm.toLowerCase()) ||
        sys.description?.toLowerCase().includes(sourceSearchTerm.toLowerCase())
      );
    }

    return systems;
  }, [sourceSystems, sourceCategory, sourceSearchTerm, categories, tables]);

  const filteredDatabases = useMemo(() => {
    // Gather all DBs from selected systems
    let dbs = selectedSystems.flatMap(sysId => 
      sourceSystems.find(sys => sys.id === sysId)?.databases || []
    );

    if (filters.platform) {
      dbs = dbs.filter(db => 
        db.platform?.toLowerCase().includes(filters.platform.toLowerCase())
      );
    }

    if (filters.dbType) {
      dbs = dbs.filter(db => 
        db.type?.toLowerCase().includes(filters.dbType.toLowerCase())
      );
    }

    if (searchTerm) {
      dbs = dbs.filter(db =>
        db.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        db.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    return dbs;
  }, [selectedSystems, sourceSystems, filters, searchTerm]);

  // -- Handlers --
  const handleSystemSelection = (sysId: string) => {
    setSelectedSystems(prev => {
      const isSelected = prev.includes(sysId);
      if (isSelected) {
        // Remove system from selection, also remove any of its DBs from selectedDatabases
        const systemDatabases = sourceSystems
          .find(sys => sys.id === sysId)
          ?.databases.map(db => db.id) || [];
        setSelectedDatabases(prevDBs => prevDBs.filter(id => !systemDatabases.includes(id)));
        return prev.filter(id => id !== sysId);
      } else {
        return [...prev, sysId];
      }
    });
    setViewMode('databases');
  };

  const handleDatabaseSelection = (dbId: string) => {
    setSelectedDatabases(prev => {
      const isSelected = prev.includes(dbId);
      if (isSelected) {
        return prev.filter(id => id !== dbId);
      } else {
        return [...prev, dbId];
      }
    });
    setViewMode('tables');
    setSelectedTable(null);
  };

  const handleTableSelection = (tableId: string) => {
    setSelectedTable(tableId);
    setViewMode('fields');
  };

  // Helpers to get current data based on selection
  const getAllTables = () => {
    return selectedDatabases.flatMap(dbId => {
      const database = databases.find(db => db.id === dbId);
      if (!database) return [];
      return tables.filter(table => table.database_id === database.id);
    });
  };

  const getCurrentTable = () => {
    if (!selectedTable) return null;
    const table = tables.find(t => t.id === selectedTable);
    if (!table) return null;
    return {
      ...table,
      fields: fields.filter(f => f.table_id === table.id)
    };
  };

  // -- Excel Export --
  const exportToExcel = (level: 'systems' | 'databases' | 'tables' | 'fields') => {
    let data: any[] = [];
    
    switch (level) {
      case 'systems':
        data = sourceSystems.map(sys => ({
          'System Name': sys.name,
          'Description': sys.description,
          'Category': sys.category,
          'Total Databases': sys.databases.length
        }));
        break;
      case 'databases':
        data = filteredDatabases.map(db => ({
          'Database Name': db.name,
          'Description': db.description,
          'Type': db.type,
          'Platform': db.platform,
          'Location': db.location,
          'Version': db.version,
          'Total Tables': db.totalTables,
          'Source System': sourceSystems.find(sys => 
            sys.databases.some(sysDb => sysDb.id === db.id)
          )?.name
        }));
        break;
      case 'tables':
        data = getAllTables().map(table => ({
          'Table Name': table.name,
          'Description': table.description,
          'Total Fields': fields.filter(f => f.table_id === table.id).length,
          'Database': databases.find(db => db.id === table.database_id)?.name,
          'Category': categories.find(cat => cat.id === table.category_id)?.name || 'Uncategorized'
        }));
        break;
      case 'fields':
        const table = getCurrentTable();
        if (table) {
          data = table.fields.map(field => ({
            'Field Name': field.name,
            'Data Type': field.type,
            'Description': field.description,
            'Nullable': field.nullable ? 'Yes' : 'No',
            'Primary Key': field.is_primary_key ? 'Yes' : 'No',
            'Foreign Key': field.is_foreign_key ? 'Yes' : 'No',
            'Default Value': field.default_value,
            'Referenced Table': field.referenced_table,
            'Referenced Column': field.referenced_column
          }));
        }
        break;
    }

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Data');
    XLSX.writeFile(wb, `data-dictionary-${level}.xlsx`);
  };

  // -- Card Renderers --
  const renderDatabaseCard = (db: DatabaseType) => (
    <div 
      key={db.id}
      className={`bg-white rounded-lg shadow-md overflow-hidden cursor-pointer transition-all ${
        selectedDatabases.includes(db.id) ? 'ring-2 ring-[#003B7E]' : ''
      }`}
      onClick={() => handleDatabaseSelection(db.id)}
    >
      <div className="bg-[#003B7E] p-4 text-white">
        <div className="flex items-center space-x-2">
          <Database className="h-5 w-5" />
          <h3 className="text-lg font-semibold">{db.name}</h3>
        </div>
      </div>
      <div className="p-4">
        <p className="text-gray-600 mb-4">{db.description}</p>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            <HardDrive className="h-4 w-4 text-gray-500" />
            <span className="text-sm">{db.type}</span>
          </div>
          <div className="flex items-center space-x-2">
            <Server className="h-4 w-4 text-gray-500" />
            <span className="text-sm">{db.platform}</span>
          </div>
          <div className="flex items-center space-x-2">
            <Table2 className="h-4 w-4 text-gray-500" />
            {loadingTables && selectedDatabases.includes(db.id) ? (
              <Loader2 className="h-4 w-4 animate-spin text-[#003B7E]" />
            ) : (
              <span className="text-sm">
                {db.totalTables} Tables
              </span>
            )}
          </div>
          <div className="text-sm text-gray-500">
            {db.location}
          </div>
        </div>
      </div>
    </div>
  );

  // -- Main Render --
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#003B7E]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f]"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Bar & Export */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-2">Data Dictionary</h1>
          <p className="text-gray-600">
            Browse and search through all available source systems, databases, tables, and fields.
          </p>
        </div>
        <button
          onClick={() => exportToExcel(viewMode)}
          className="flex items-center space-x-2 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
        >
          <Download className="h-4 w-4" />
          <span>Export to Excel</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        {viewMode === 'systems' && (
          <>
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search source systems..."
                className="pl-10 pr-4 py-2 w-full rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
                value={sourceSearchTerm}
                onChange={(e) => setSourceSearchTerm(e.target.value)}
              />
            </div>
            <select
              value={sourceCategory}
              onChange={(e) => setSourceCategory(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
            >
              <option value="">All Categories</option>
              {categories.map(category => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </>
        )}

        {viewMode === 'databases' && (
          <div className="flex gap-4">
            <select
              value={filters.platform}
              onChange={(e) => setFilters(prev => ({ ...prev, platform: e.target.value }))}
              className="rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
            >
              <option value="">All Platforms</option>
              {Array.from(new Set(databases.map(db => db.platform)))
                .filter(Boolean)
                .map(platform => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
            </select>
            <select
              value={filters.dbType}
              onChange={(e) => setFilters(prev => ({ ...prev, dbType: e.target.value }))}
              className="rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
            >
              <option value="">All Database Types</option>
              {Array.from(new Set(databases.map(db => db.type)))
                .filter(Boolean)
                .map(type => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
            </select>
          </div>
        )}
      </div>

      {/* Breadcrumb */}
      {viewMode !== 'systems' && (
        <div className="flex items-center space-x-2 text-sm">
          <button
            onClick={() => {
              setViewMode('systems');
              setSelectedSystems([]);
              setSelectedDatabases([]);
              setSelectedTable(null);
            }}
            className="text-[#003B7E] hover:underline"
          >
            Source Systems
          </button>
          {viewMode !== 'systems' && (
            <>
              <span>/</span>
              <button
                onClick={() => {
                  setViewMode('databases');
                  setSelectedDatabases([]);
                  setSelectedTable(null);
                }}
                className="text-[#003B7E] hover:underline"
              >
                Databases
              </button>
            </>
          )}
          {viewMode === 'tables' && (
            <>
              <span>/</span>
              <span>Tables</span>
            </>
          )}
          {viewMode === 'fields' && (
            <>
              <span>/</span>
              <button
                onClick={() => {
                  setViewMode('tables');
                  setSelectedTable(null);
                }}
                className="text-[#003B7E] hover:underline"
              >
                Tables
              </button>
              <span>/</span>
              {/* Final breadcrumb changed from table name to "Fields": */}
              <span>Fields</span>
            </>
          )}
        </div>
      )}

      {/* Systems View */}
      {viewMode === 'systems' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSystems.map(system => (
            <div 
              key={system.id}
              className={`bg-white rounded-lg shadow-md overflow-hidden cursor-pointer transition-all ${
                selectedSystems.includes(system.id) ? 'ring-2 ring-[#003B7E]' : ''
              }`}
              onClick={() => handleSystemSelection(system.id)}
            >
              <div className="bg-[#003B7E] p-4 text-white">
                <div className="flex items-center space-x-2">
                  <Building2 className="h-5 w-5" />
                  <h3 className="text-lg font-semibold">{system.name}</h3>
                </div>
              </div>
              <div className="p-4">
                <p className="text-gray-600 mb-4">{system.description}</p>
                <p className="text-xs italic mb-2">Category: {system.category}</p>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <Database className="h-4 w-4" />
                  <span>
                    {system.databases.length} Database
                    {system.databases.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Databases View */}
      {viewMode === 'databases' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {loadingDatabases ? (
            <div className="col-span-2 flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#003B7E]" />
            </div>
          ) : (
            filteredDatabases.map(db => renderDatabaseCard(db))
          )}
        </div>
      )}

      {/* Tables View */}
      {viewMode === 'tables' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {getAllTables().map(table => (
            <div
              key={table.id}
              className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => handleTableSelection(table.id)}
            >
              <div className="p-4">
                <div className="flex items-center space-x-2 mb-3">
                  <Table2 className="h-5 w-5 text-[#003B7E]" />
                  <h3 className="font-semibold">{table.name}</h3>
                </div>
                <p className="text-sm text-gray-600 mb-3">{table.description}</p>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-500">
                      {fields.filter(f => f.table_id === table.id).length} Fields
                    </div>
                    {table.category_id && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        {categories.find(cat => cat.id === table.category_id)?.name}
                      </span>
                    )}
                  </div>
                  {table.record_count !== undefined && (
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-500">Records:</span>
                      <span className="font-medium text-gray-700">
                        {table.record_count.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {table.last_imported && (
                    <div className="flex justify-between items-center text-xs text-gray-400">
                      <span>Last imported:</span>
                      <span>{new Date(table.last_imported).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Fields View */}
      {viewMode === 'fields' && getCurrentTable() && (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="p-6">
            <div className="flex justify-between items-start mb-6">
              <div className="flex-1">
                <h3 className="text-xl font-semibold mb-2">
                  {getCurrentTable()?.name}
                </h3>
                <p className="text-gray-600 mb-3">
                  {getCurrentTable()?.description}
                </p>
                <div className="flex gap-4 text-sm text-gray-500">
                  {getCurrentTable()?.record_count !== undefined && (
                    <div>
                      <span className="font-medium">Records:</span>{' '}
                      <span className="text-gray-700">{getCurrentTable()?.record_count.toLocaleString()}</span>
                    </div>
                  )}
                  {getCurrentTable()?.last_imported && (
                    <div>
                      <span className="font-medium">Last imported:</span>{' '}
                      <span className="text-gray-700">
                        {new Date(getCurrentTable()!.last_imported).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              {getCurrentTable()?.category_id && (
                <span className="text-sm bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                  {categories.find(cat => cat.id === getCurrentTable()?.category_id)?.name}
                </span>
              )}
            </div>
            
            {loadingFields ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-[#003B7E]" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Field Name</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Data Type</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Description</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Constraints</th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">References</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getCurrentTable()?.fields.map(field => (
                      <tr key={field.id} className="border-t">
                        <td className="px-4 py-3">
                          <div className="font-medium">{field.name}</div>
                          {(field.is_primary_key || field.is_foreign_key) && (
                            <div className="flex space-x-2 mt-1">
                              {field.is_primary_key && (
                                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                  PK
                                </span>
                              )}
                              {field.is_foreign_key && (
                                <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
                                  FK
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">{field.type}</td>
                        <td className="px-4 py-3 text-sm">{field.description}</td>
                        <td className="px-4 py-3 text-sm">
                          {!field.nullable && (
                            <span className="text-red-600">Required</span>
                          )}
                          {field.default_value && (
                            <div className="text-gray-500">
                              Default: {field.default_value}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {field.is_foreign_key && field.referenced_table && (
                            <div className="text-sm">
                              <span className="font-medium">{field.referenced_table}</span>
                              {field.referenced_column && (
                                <span className="text-gray-500">
                                  .{field.referenced_column}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default DataDictionary;
