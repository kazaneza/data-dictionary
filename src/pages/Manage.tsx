import React, { useState, useEffect, useMemo } from 'react';
import { 
  Database as DatabaseIcon,
  Table2,
  FileSpreadsheet,
  Tags,
  Trash2,
  ArrowLeft,
  AlertCircle,
  Edit,
  Search
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { Link } from 'react-router-dom';
import * as api from '../lib/api';
import EditModal from '../components/EditModal';

function Manage() {
  const [activeSection, setActiveSection] = useState<'sources' | 'databases' | 'tables' | 'fields' | 'categories'>('sources');

  // Data states
  const [sources, setSources] = useState<api.SourceSystem[]>([]);
  const [databases, setDatabases] = useState<api.Database[]>([]);
  const [tables, setTables] = useState<api.Table[]>([]);
  const [fields, setFields] = useState<api.Field[]>([]);
  const [categories, setCategories] = useState<api.Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Search and filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [databaseFilter, setDatabaseFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // Edit modal states
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [srcData, dbData, tblData, fldData, catData] = await Promise.all([
          api.fetchSources(),
          api.fetchDatabases(),
          api.fetchTables(),
          api.fetchFields(),
          api.fetchCategories()
        ]);

        setSources(srcData);
        setDatabases(dbData);
        setTables(tblData);
        setFields(fldData);
        setCategories(catData);
        setLoading(false);
      } catch (error) {
        console.error('Error loading initial data:', error);
        toast.error('Failed to load initial data');
        setLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  const filteredData = useMemo(() => {
    let data: any[] = [];
    const searchLower = searchTerm.toLowerCase();

    switch (activeSection) {
      case 'sources':
        data = sources.filter(source => {
          const matchesSearch = 
            source.name.toLowerCase().includes(searchLower) ||
            source.description?.toLowerCase().includes(searchLower) ||
            source.category?.toLowerCase().includes(searchLower);
          
          const matchesCategory = !categoryFilter || source.category === categoryFilter;
          
          return matchesSearch && matchesCategory;
        });
        break;

      case 'databases':
        data = databases.filter(db => {
          const matchesSearch = 
            db.name.toLowerCase().includes(searchLower) ||
            db.description?.toLowerCase().includes(searchLower);
          
          const matchesPlatform = !platformFilter || db.platform === platformFilter;
          
          return matchesSearch && matchesPlatform;
        });
        break;

      case 'tables':
        data = tables.filter(table => {
          const matchesSearch = 
            table.name.toLowerCase().includes(searchLower) ||
            table.description?.toLowerCase().includes(searchLower);
          
          const matchesDatabase = !databaseFilter || table.database_id === databaseFilter;
          
          return matchesSearch && matchesDatabase;
        });
        break;

      case 'fields':
        data = fields.filter(field => {
          const matchesSearch = 
            field.name.toLowerCase().includes(searchLower) ||
            field.description?.toLowerCase().includes(searchLower);
          
          const matchesTable = !tableFilter || field.table_id === tableFilter;
          const matchesType = !typeFilter || field.type.toLowerCase().includes(typeFilter.toLowerCase());
          
          return matchesSearch && matchesTable && matchesType;
        });
        break;

      case 'categories':
        data = categories.filter(category =>
          category.name.toLowerCase().includes(searchLower) ||
          category.description?.toLowerCase().includes(searchLower)
        );
        break;
    }

    return data;
  }, [
    activeSection,
    sources,
    databases,
    tables,
    fields,
    categories,
    searchTerm,
    categoryFilter,
    platformFilter,
    databaseFilter,
    tableFilter,
    typeFilter
  ]);

  const handleEdit = (item: any) => {
    setEditingItem(item);
    setEditModalOpen(true);
  };

  const handleSaveEdit = async (updatedData: any) => {
    try {
      let result;
      switch (activeSection) {
        case 'sources':
          result = await api.updateSource(editingItem.id, updatedData);
          setSources(sources.map(s => s.id === result.id ? result : s));
          break;
        case 'databases':
          result = await api.updateDatabase(editingItem.id, updatedData);
          setDatabases(databases.map(d => d.id === result.id ? result : d));
          break;
        case 'tables':
          result = await api.updateTable(editingItem.id, updatedData);
          setTables(tables.map(t => t.id === result.id ? result : t));
          break;
        case 'fields':
          result = await api.updateField(editingItem.id, updatedData);
          setFields(fields.map(f => f.id === result.id ? result : f));
          break;
        case 'categories':
          result = await api.updateCategory(editingItem.id, updatedData);
          setCategories(categories.map(c => c.id === result.id ? result : c));
          break;
      }
      toast.success('Updated successfully');
    } catch (error) {
      console.error('Failed to update:', error);
      toast.error('Failed to update');
    }
  };

  const handleDelete = async (item: any) => {
    const getRelatedItems = () => {
      switch (activeSection) {
        case 'sources': {
          const relatedDatabases = databases.filter(db => db.source_id === item.id);
          const relatedTables = tables.filter(table => 
            relatedDatabases.some(db => db.id === table.database_id)
          );
          const relatedFields = fields.filter(field =>
            relatedTables.some(table => table.id === field.table_id)
          );
          return {
            databases: relatedDatabases.length,
            tables: relatedTables.length,
            fields: relatedFields.length
          };
        }
        case 'databases': {
          const relatedTables = tables.filter(table => table.database_id === item.id);
          const relatedFields = fields.filter(field =>
            relatedTables.some(table => table.id === field.table_id)
          );
          return {
            tables: relatedTables.length,
            fields: relatedFields.length
          };
        }
        case 'tables': {
          const relatedFields = fields.filter(field => field.table_id === item.id);
          return {
            fields: relatedFields.length
          };
        }
        default:
          return {};
      }
    };

    const relatedItems = getRelatedItems();
    const relatedItemsText = Object.entries(relatedItems)
      .map(([key, count]) => `${count} ${key}`)
      .join(', ');

    const confirmMessage = `Are you sure you want to delete "${item.name}"?\n\n` +
      (relatedItemsText ? `This will also delete: ${relatedItemsText}` : '');

    if (!window.confirm(confirmMessage)) return;

    try {
      switch (activeSection) {
        case 'sources':
          await api.deleteSource(item.id);
          setSources(sources.filter(s => s.id !== item.id));
          setDatabases(databases.filter(db => db.source_id !== item.id));
          setTables(tables.filter(t => !databases.some(db => db.source_id === item.id && db.id === t.database_id)));
          setFields(fields.filter(f => !tables.some(t => t.database_id === item.database_id && t.id === f.table_id)));
          break;
        case 'databases':
          await api.deleteDatabase(item.id);
          setDatabases(databases.filter(db => db.id !== item.id));
          setTables(tables.filter(t => t.database_id !== item.id));
          setFields(fields.filter(f => !tables.some(t => t.database_id === item.id && t.id === f.table_id)));
          break;
        case 'tables':
          await api.deleteTable(item.id);
          setTables(tables.filter(t => t.id !== item.id));
          setFields(fields.filter(f => f.table_id !== item.id));
          break;
        case 'fields':
          await api.deleteField(item.id);
          setFields(fields.filter(f => f.id !== item.id));
          break;
        case 'categories':
          await api.deleteCategory(item.id);
          setCategories(categories.filter(c => c.id !== item.id));
          setTables(tables.map(t => t.category_id === item.id ? { ...t, category_id: null } : t));
          break;
      }
      toast.success('Deleted successfully');
    } catch (error) {
      console.error('Failed to delete:', error);
      toast.error('Failed to delete');
    }
  };

  const renderFilters = () => {
    switch (activeSection) {
      case 'sources':
        return (
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-4 py-2"
          >
            <option value="">All Categories</option>
            {Array.from(new Set(sources.map(src => src.category)))
              .filter(Boolean)
              .map(category => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
          </select>
        );

      case 'databases':
        return (
          <div className="flex space-x-4">
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2"
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
          </div>
        );

      case 'tables':
        return (
          <div className="flex space-x-4">
            <select
              value={databaseFilter}
              onChange={(e) => setDatabaseFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2"
            >
              <option value="">All Databases</option>
              {databases.map(db => (
                <option key={db.id} value={db.id}>
                  {db.name}
                </option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2"
            >
              <option value="">All Categories</option>
              {categories.map(category => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
        );

      case 'fields':
        return (
          <div className="flex space-x-4">
            <select
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-4 py-2"
            >
              <option value="">All Tables</option>
              {tables.map(table => (
                <option key={table.id} value={table.id}>
                  {table.name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              placeholder="Filter by type..."
              className="rounded-lg border border-gray-300 px-4 py-2"
            />
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#003B7E]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/dictionary"
            className="text-[#003B7E] hover:text-[#002c5f] flex items-center"
          >
            <ArrowLeft className="h-5 w-5 mr-1" />
            Back to Dictionary
          </Link>
          <h1 className="text-2xl font-bold">Manage Data Dictionary</h1>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex space-x-4">
        <button
          onClick={() => {
            setActiveSection('sources');
            setSearchTerm('');
            setCategoryFilter('');
            setPlatformFilter('');
            setDatabaseFilter('');
            setTableFilter('');
            setTypeFilter('');
          }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'sources'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Source Systems
        </button>
        <button
          onClick={() => {
            setActiveSection('databases');
            setSearchTerm('');
            setCategoryFilter('');
            setPlatformFilter('');
            setDatabaseFilter('');
            setTableFilter('');
            setTypeFilter('');
          }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'databases'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Databases
        </button>
        <button
          onClick={() => {
            setActiveSection('tables');
            setSearchTerm('');
            setCategoryFilter('');
            setPlatformFilter('');
            setDatabaseFilter('');
            setTableFilter('');
            setTypeFilter('');
          }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'tables'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Tables
        </button>
        <button
          onClick={() => {
            setActiveSection('fields');
            setSearchTerm('');
            setCategoryFilter('');
            setPlatformFilter('');
            setDatabaseFilter('');
            setTableFilter('');
            setTypeFilter('');
          }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'fields'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Fields
        </button>
        <button
          onClick={() => {
            setActiveSection('categories');
            setSearchTerm('');
            setCategoryFilter('');
            setPlatformFilter('');
            setDatabaseFilter('');
            setTableFilter('');
            setTypeFilter('');
          }}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'categories'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Categories
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={`Search ${activeSection}...`}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#003B7E]/50"
          />
        </div>
        {renderFilters()}
      </div>

      {/* Warning Message */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertCircle className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              Warning: Deleting items will also remove all related data. This action cannot be undone.
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-4">
        {filteredData.map((item) => (
          <div key={item.id} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold flex items-center">
                  {activeSection === 'sources' && <DatabaseIcon className="h-5 w-5 mr-2 text-[#003B7E]" />}
                  {activeSection === 'databases' && <Table2 className="h-5 w-5 mr-2 text-[#003B7E]" />}
                  {activeSection === 'tables' && <FileSpreadsheet className="h-5 w-5 mr-2 text-[#003B7E]" />}
                  {activeSection === 'categories' && <Tags className="h-5 w-5 mr-2 text-[#003B7E]" />}
                  {item.name}
                </h3>
                <p className="text-gray-600 mt-1">{item.description}</p>
                {activeSection === 'sources' && item.category && (
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full mt-2 inline-block">
                    {item.category}
                  </span>
                )}
                {activeSection === 'databases' && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {item.type && (
                      <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
                        {item.type}
                      </span>
                    )}
                    {item.platform && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        {item.platform}
                      </span>
                    )}
                  </div>
                )}
                {activeSection === 'fields' && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
                      {item.type}
                    </span>
                    {item.is_primary_key && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        Primary Key
                      </span>
                    )}
                    {item.is_foreign_key && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        Foreign Key
                      </span>
                    )}
                    {item.nullable && (
                      <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded-full">
                        Nullable
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleEdit(item)}
                  className="text-blue-600 hover:text-blue-800 p-2"
                  title={`Edit ${activeSection.slice(0, -1)}`}
                >
                  <Edit className="h-5 w-5" />
                </button>
                <button
                  onClick={() => handleDelete(item)}
                  className="text-red-600 hover:text-red-800 p-2"
                  title={`Delete ${activeSection.slice(0, -1)}`}
                >
                  <Trash2 className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        ))}
        {filteredData.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No {activeSection} found
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <EditModal
          isOpen={editModalOpen}
          onClose={() => {
            setEditModalOpen(false);
            setEditingItem(null);
          }}
          onSave={handleSaveEdit}
          title={`Edit ${activeSection.slice(0, -1)}`}
          data={editingItem}
          type={activeSection.slice(0, -1) as any}
          categories={categories}
          sources={sources}
          databases={databases}
        />
      )}
    </div>
  );
}

export default Manage;