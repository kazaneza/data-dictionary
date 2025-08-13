import React, { useState, useEffect } from 'react';
import {
  Plus,
  Database as DatabaseIcon,
  Table2,
  FileSpreadsheet,
  Tags,
  Save,
  Upload
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import * as api from '../lib/api';
import BulkUploadModal from '../components/BulkUploadModal';

function Settings() {
  const [activeTab, setActiveTab] = useState<'add' | 'categories'>('add');
  const [bulkUploadModalOpen, setBulkUploadModalOpen] = useState(false);

  // Data states
  const [sources, setSources] = useState<api.SourceSystem[]>([]);
  const [databases, setDatabases] = useState<api.Database[]>([]);
  const [tables, setTables] = useState<api.Table[]>([]);
  const [fields, setFields] = useState<api.Field[]>([]);
  const [categories, setCategories] = useState<api.Category[]>([]);

  const [newSource, setNewSource] = useState({ name: '', description: '', category: '' });
  const [newDatabase, setNewDatabase] = useState({
    source_id: '',
    name: '',
    description: '',
    type: '',
    platform: '',
    location: '',
    version: '',
  });
  const [newTable, setNewTable] = useState({
    sourceId: '',
    databaseId: '',
    categoryId: '',
    name: '',
    description: '',
  });
  const [newField, setNewField] = useState({
    sourceId: '',
    databaseId: '',
    tableId: '',
    name: '',
    type: '',
    description: '',
    nullable: false,
    isPrimaryKey: false,
    isForeignKey: false,
    defaultValue: '',
  });
  const [newCategory, setNewCategory] = useState({
    name: '',
    description: '',
  });

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
      } catch (error) {
        console.error('Error loading initial data:', error);
        toast.error('Failed to load initial data');
      }
    };

    fetchInitialData();
  }, []);

  const handleAddSource = async () => {
    if (!newSource.name) {
      toast.error('Please enter a Source Name.');
      return;
    }
    try {
      const createdSource = await api.createSource(newSource);
      setSources([...sources, createdSource]);
      setNewSource({ name: '', description: '', category: '' });
      toast.success(`Source "${createdSource.name}" added successfully!`);
    } catch (error) {
      console.error('Failed to create source:', error);
    }
  };

  const handleAddDatabase = async () => {
    if (!newDatabase.source_id) {
      toast.error('Please select a Source for this Database.');
      return;
    }
    if (!newDatabase.name) {
      toast.error('Please enter a Database Name.');
      return;
    }

    try {
      const createdDb = await api.createDatabase(newDatabase);
      setDatabases([...databases, createdDb]);
      setNewDatabase({
        source_id: '',
        name: '',
        description: '',
        type: '',
        platform: '',
        location: '',
        version: '',
      });
      toast.success(`Database "${createdDb.name}" added successfully!`);
    } catch (error) {
      console.error('Failed to create database:', error);
    }
  };

  const handleAddTable = async () => {
    if (!newTable.sourceId) {
      toast.error('Please select a Source first.');
      return;
    }
    if (!newTable.databaseId) {
      toast.error('Please select a Database.');
      return;
    }
    if (!newTable.name) {
      toast.error('Please enter a Table Name.');
      return;
    }

    try {
      const payload = {
        database_id: newTable.databaseId,
        category_id: newTable.categoryId || undefined,
        name: newTable.name,
        description: newTable.description,
      };

      const createdTable = await api.createTable(payload);
      setTables([...tables, createdTable]);
      setNewTable({
        sourceId: '',
        databaseId: '',
        categoryId: '',
        name: '',
        description: '',
      });
      toast.success(`Table "${createdTable.name}" added successfully!`);
    } catch (error) {
      console.error('Failed to create table:', error);
    }
  };

  const handleAddField = async () => {
    if (!newField.sourceId) {
      toast.error('Please select a Source first.');
      return;
    }
    if (!newField.databaseId) {
      toast.error('Please select a Database.');
      return;
    }
    if (!newField.tableId) {
      toast.error('Please select a Table.');
      return;
    }
    if (!newField.name) {
      toast.error('Please enter a Field Name.');
      return;
    }

    try {
      const payload = {
        table_id: newField.tableId,
        name: newField.name,
        type: newField.type,
        description: newField.description,
        nullable: newField.nullable,
        is_primary_key: newField.isPrimaryKey,
        is_foreign_key: newField.isForeignKey,
        default_value: newField.defaultValue || undefined,
      };

      const createdField = await api.createField(payload);
      setFields([...fields, createdField]);
      setNewField({
        sourceId: '',
        databaseId: '',
        tableId: '',
        name: '',
        type: '',
        description: '',
        nullable: false,
        isPrimaryKey: false,
        isForeignKey: false,
        defaultValue: '',
      });
      toast.success(`Field "${createdField.name}" added successfully!`);
    } catch (error) {
      console.error('Failed to create field:', error);
    }
  };

  const handleAddCategory = async () => {
    if (!newCategory.name) {
      toast.error('Please enter a Category Name.');
      return;
    }
    try {
      const createdCategory = await api.createCategory(newCategory);
      setCategories([...categories, createdCategory]);
      setNewCategory({ name: '', description: '' });
      toast.success(`Category "${createdCategory.name}" added successfully!`);
    } catch (error) {
      console.error('Failed to create category:', error);
    }
  };

  const handleBulkUploadSuccess = async () => {
    // Refresh all data
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
  };

  const filteredDatabasesForTable = databases.filter(
    (db) => db.source_id === newTable.sourceId
  );

  const filteredDatabasesForField = databases.filter(
    (db) => db.source_id === newField.sourceId
  );

  const filteredTablesForField = tables.filter(
    (tbl) => tbl.database_id === newField.databaseId
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          onClick={() => setBulkUploadModalOpen(true)}
          className="flex items-center space-x-2 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
        >
          <Upload className="h-4 w-4" />
          <span>Bulk Upload</span>
        </button>
      </div>

      {/* TABS */}
      <div className="flex space-x-4">
        <button
          onClick={() => setActiveTab('add')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'add'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Add Data
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            activeTab === 'categories'
              ? 'bg-[#003B7E] text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          Categories
        </button>
      </div>

      {/* TAB CONTENT: ADD DATA */}
      {activeTab === 'add' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="space-y-8">
            {/* ADD SOURCE */}
            <div className="border-b pb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <DatabaseIcon className="h-5 w-5 mr-2" />
                Add Source System
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    System Name
                  </label>
                  <input
                    type="text"
                    value={newSource.name}
                    onChange={(e) =>
                      setNewSource({ ...newSource, name: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., T24 Core Banking"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={newSource.description}
                    onChange={(e) =>
                      setNewSource({ ...newSource, description: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="Brief description of the system"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Category
                  </label>
                  <input
                    type="text"
                    value={newSource.category}
                    onChange={(e) =>
                      setNewSource({ ...newSource, category: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., Core Banking"
                  />
                </div>
              </div>
              <button
                onClick={handleAddSource}
                className="mt-4 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
              >
                Add Source
              </button>
            </div>

            {/* ADD DATABASE */}
            <div className="border-b pb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Table2 className="h-5 w-5 mr-2" />
                Add Database
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source
                  </label>
                  <select
                    value={newDatabase.source_id}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, source_id: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Source --</option>
                    {sources.map((src) => (
                      <option key={src.id} value={src.id}>
                        {src.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Database Name
                  </label>
                  <input
                    type="text"
                    value={newDatabase.name}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, name: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., Customer Database"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={newDatabase.description}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, description: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="Brief description"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <input
                    type="text"
                    value={newDatabase.type}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, type: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., Oracle, PostgreSQL, or custom type"
                    list="database-types"
                  />
                  <datalist id="database-types">
                    <option value="Oracle" />
                    <option value="PostgreSQL" />
                    <option value="MSSQL" />
                    <option value="MySQL" />
                    <option value="MongoDB" />
                    <option value="MariaDB" />
                    <option value="SQLite" />
                    <option value="Cassandra" />
                    <option value="Redis" />
                    <option value="DynamoDB" />
                    <option value="Elasticsearch" />
                    <option value="Neo4j" />
                    <option value="CouchDB" />
                    <option value="Firebase" />
                    <option value="Supabase" />
                  </datalist>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Platform
                  </label>
                  <input
                    type="text"
                    value={newDatabase.platform}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, platform: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., Linux, Windows, or custom platform"
                    list="platforms"
                  />
                  <datalist id="platforms">
                    <option value="Linux" />
                    <option value="Windows" />
                    <option value="macOS" />
                    <option value="Docker" />
                    <option value="Kubernetes" />
                    <option value="AWS" />
                    <option value="Azure" />
                    <option value="GCP" />
                    <option value="OpenShift" />
                    <option value="VMware" />
                    <option value="Bare Metal" />
                    <option value="Cloud" />
                    <option value="On-Premise" />
                    <option value="Hybrid Cloud" />
                    <option value="Private Cloud" />
                  
                  </datalist>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Location (IP / URL)
                  </label>
                  <input
                    type="text"
                    value={newDatabase.location}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, location: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., 192.168.0.10"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Version
                  </label>
                  <input
                    type="text"
                    value={newDatabase.version}
                    onChange={(e) =>
                      setNewDatabase({ ...newDatabase, version: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., 19c Enterprise"
                  />
                </div>
              </div>
              <button
                onClick={handleAddDatabase}
                className="mt-4 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
              >
                Add Database
              </button>
            </div>

            {/* ADD TABLE */}
            <div className="border-b pb-8">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <FileSpreadsheet className="h-5 w-5 mr-2" />
                Add Table
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source
                  </label>
                  <select
                    value={newTable.sourceId}
                    onChange={(e) =>
                      setNewTable({
                        ...newTable,
                        sourceId: e.target.value,
                        databaseId: '',
                      })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Source --</option>
                    {sources.map((src) => (
                      <option key={src.id} value={src.id}>
                        {src.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Database
                  </label>
                  <select
                    value={newTable.databaseId}
                    onChange={(e) =>
                      setNewTable({ ...newTable, databaseId: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Database --</option>
                    {filteredDatabasesForTable.map((db) => (
                      <option key={db.id} value={db.id}>
                        {db.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Category
                  </label>
                  <select
                    value={newTable.categoryId}
                    onChange={(e) =>
                      setNewTable({ ...newTable, categoryId: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- None --</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Table Name
                  </label>
                  <input
                    type="text"
                    value={newTable.name}
                    onChange={(e) =>
                      setNewTable({ ...newTable, name: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., CUSTOMER"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={newTable.description}
                    onChange={(e) =>
                      setNewTable({ ...newTable, description: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="Brief description of the table"
                  />
                </div>
              </div>
              <button
                onClick={handleAddTable}
                className="mt-4 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
              >
                Add Table
              </button>
            </div>

            {/* ADD FIELD */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Plus className="h-5 w-5 mr-2" />
                Add Field
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source
                  </label>
                  <select
                    value={newField.sourceId}
                    onChange={(e) =>
                      setNewField({
                        ...newField,
                        sourceId: e.target.value,
                        databaseId: '',
                        tableId: '',
                      })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Source --</option>
                    {sources.map((src) => (
                      <option key={src.id} value={src.id}>
                        {src.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Database
                  </label>
                  <select
                    value={newField.databaseId}
                    onChange={(e) =>
                      setNewField({
                        ...newField,
                        databaseId: e.target.value,
                        tableId: '',
                      })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Database --</option>
                    {filteredDatabasesForField.map((db) => (
                      <option key={db.id} value={db.id}>
                        {db.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Table
                  </label>
                  <select
                    value={newField.tableId}
                    onChange={(e) =>
                      setNewField({ ...newField, tableId: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  >
                    <option value="">-- Select Table --</option>
                    {filteredTablesForField.map((tbl) => (
                      <option key={tbl.id} value={tbl.id}>
                        {tbl.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Field Name
                  </label>
                  <input
                    type="text"
                    value={newField.name}
                    onChange={(e) =>
                      setNewField({ ...newField, name: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., customer_id"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data Type
                  </label>
                  <input
                    type="text"
                    value={newField.type}
                    onChange={(e) =>
                      setNewField({ ...newField, type: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="e.g., VARCHAR(50)"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={newField.description}
                    onChange={(e) =>
                      setNewField({ ...newField, description: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="Brief description of this field"
                  />
                </div>
                <div className="col-span-2 flex space-x-4">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={newField.nullable}
                      onChange={(e) =>
                        setNewField({ ...newField, nullable: e.target.checked })
                      }
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Nullable</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={newField.isPrimaryKey}
                      onChange={(e) =>
                        setNewField({ ...newField, isPrimaryKey: e.target.checked })
                      }
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Primary Key</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={newField.isForeignKey}
                      onChange={(e) =>
                        setNewField({ ...newField, isForeignKey: e.target.checked })
                      }
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Foreign Key</span>
                  </label>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Default Value
                  </label>
                  <input
                    type="text"
                    value={newField.defaultValue}
                    onChange={(e) =>
                      setNewField({ ...newField, defaultValue: e.target.value })
                    }
                    className="w-full rounded-lg border border-gray-300 px-4 py-2"
                    placeholder="Default value (optional)"
                  />
                </div>
              </div>
              <button
                onClick={handleAddField}
                className="mt-4 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
              >
                Add Field
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: CATEGORIES */}
      {activeTab === 'categories' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <Tags className="h-5 w-5 mr-2" />
              Add New Category
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category Name
                </label>
                <input
                  type="text"
                  value={newCategory.name}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, name: e.target.value })
                  }
                  className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  placeholder="e.g., Customer Data"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={newCategory.description}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, description: e.target.value })
                  }
                  className="w-full rounded-lg border border-gray-300 px-4 py-2"
                  placeholder="Category description"
                />
              </div>
            </div>
            <button
              onClick={handleAddCategory}
              className="mt-4 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors flex items-center"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Category
            </button>
          </div>

          {/* Existing Categories */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Existing Categories</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {categories.map((cat) => {
                const tableCount = tables.filter((t) => t.category_id === cat.id).length;
                return (
                  <div className="border rounded-lg p-4" key={cat.id}>
                    <h4 className="font-medium">{cat.name}</h4>
                    <p className="text-sm text-gray-600 mb-2">{cat.description}</p>
                    <div className="text-sm text-[#003B7E]">
                      {tableCount} Table{tableCount !== 1 ? 's' : ''}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Bulk Upload Modal */}
      <BulkUploadModal
        isOpen={bulkUploadModalOpen}
        onClose={() => setBulkUploadModalOpen(false)}
        sources={sources}
        databases={databases}
        onSuccess={handleBulkUploadSuccess}
      />
    </div>
  );
}

export default Settings;
