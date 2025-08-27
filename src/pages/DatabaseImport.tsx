import React, { useState, useEffect } from 'react';
import { ArrowLeft, Database } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import * as api from '../lib/api';
import DatabaseInfoForm from '../components/database-import/DatabaseInfoForm';
import DatabaseCredentialsForm from '../components/database-import/DatabaseCredentialsForm';
import SchemaPreview from '../components/database-import/SchemaPreview';
import ConnectionHistory, { saveConnectionHistory, createHistoryItem } from '../components/database-import/ConnectionHistory';

interface DatabaseConfig {
  server: string;
  database: string;
  username: string;
  password: string;
  schema?: string;
  source_id: string;
  description?: string;
  type?: string;
  platform?: string;
  location?: string;
  version?: string;
}

interface TableField {
  tableName: string;
  fieldName: string;
  dataType: string;
  isNullable: string;
  isPrimaryKey: string;
  isForeignKey: string;
  defaultValue: string | null;
  description?: string;
}

interface PreviewData {
  tables: string[];
  fields: TableField[];
}

interface TableData {
  fields: TableField[];
  tableDescription: string;
}

const API_URL = 'http://10.24.37.99:8000';

export default function DatabaseImport() {
  const [step, setStep] = useState<'info' | 'credentials' | 'history'>('history');
  const [config, setConfig] = useState<DatabaseConfig>({
    server: '',
    database: '',
    username: '',
    password: '',
    schema: '',
    source_id: '',
    description: '',
    type: '',
    platform: '',
    location: '',
    version: ''
  });

  const [loading, setLoading] = useState(false);
  const [loadingDescriptions, setLoadingDescriptions] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [sources, setSources] = useState<api.SourceSystem[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [tableFields, setTableFields] = useState<TableField[]>([]);

  // Track import progress for history
  const [currentHistoryId, setCurrentHistoryId] = useState<string | null>(null);
  const [importStartTime, setImportStartTime] = useState<number | null>(null);
  const [connectionController, setConnectionController] = useState<AbortController | null>(null);

  useEffect(() => {
    const fetchSources = async () => {
      try {
        const sourcesData = await api.fetchSources();
        setSources(sourcesData);
      } catch (error) {
        console.error('Failed to fetch sources:', error);
        toast.error('Failed to load source systems');
      }
    };

    fetchSources();
    
    // Cleanup on unmount
    return () => {
      if (connectionController) {
        connectionController.abort();
      }
    };
  }, []);

  const handleConnect = async () => {
    // Cancel any existing connection
    if (connectionController) {
      connectionController.abort();
      setConnectionController(null);
    }
    
    // Create new abort controller
    const controller = new AbortController();
    setConnectionController(controller);
    
    const startTime = Date.now();
    setImportStartTime(startTime);
    
    // Create initial history entry
    const historyItem = createHistoryItem(
      config,
      'in_progress',
      0,
      0,
      [],
      undefined,
      undefined
    );
    setCurrentHistoryId(historyItem.id);
    saveConnectionHistory(historyItem);

    if (!config.source_id) {
      toast.error('Please select a source system');
      // Update history with failure
      const failedItem = createHistoryItem(
        config,
        'failed',
        0,
        0,
        [],
        'Source system not selected',
        Date.now() - startTime
      );
      failedItem.id = historyItem.id;
      saveConnectionHistory(failedItem);
      setConnectionController(null);
      return;
    }

    if (!config.server || !config.database || !config.username || !config.password) {
      toast.error('Please fill in all required fields');
      // Update history with failure
      const failedItem = createHistoryItem(
        config,
        'failed',
        0,
        0,
        [],
        'Missing required connection fields',
        Date.now() - startTime
      );
      failedItem.id = historyItem.id;
      saveConnectionHistory(failedItem);
      setConnectionController(null);
      return;
    }

    try {
      setLoading(true);
      
      // Show immediate feedback
      toast.loading('Connecting to database...', { id: 'connection' });
      
      const response = await axios.post(`${API_URL}/api/database/connect`, config, {
        signal: controller.signal,
        timeout: 120000 // 2 minute timeout for large databases
      });
      
      toast.dismiss('connection');
      
      setPreviewData(response.data);
      
      // For large datasets, don't auto-select all tables
      const tables = response.data.tables || [];
      if (tables.length <= 100) {
        setSelectedTables(tables);
      } else {
        setSelectedTables([]);
        toast.info(`Found ${tables.length} tables. Please select the ones you want to import.`);
      }
      
      // Update history with successful connection
      const successItem = createHistoryItem(
        config,
        'success',
        response.data.tables?.length || 0,
        0,
        [],
        undefined,
        Date.now() - startTime
      );
      successItem.id = historyItem.id;
      saveConnectionHistory(successItem);
      
      toast.success('Successfully connected to database');
    } catch (error: any) {
      toast.dismiss('connection');
      
      // Don't show error if request was cancelled
      if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
        toast('Connection cancelled');
        return;
      }
      
      console.error('Failed to connect:', error);
      
      // Update history with failure
      const failedItem = createHistoryItem(
        config,
        'failed',
        0,
        0,
        [],
        error.response?.data?.detail || error.message || 'Connection failed',
        Date.now() - startTime
      );
      failedItem.id = historyItem.id;
      saveConnectionHistory(failedItem);
      
      const errorMessage = error.response?.data?.detail || error.message || 'Connection failed';
      toast.error(`Failed to connect: ${errorMessage}`);
    } finally {
      setLoading(false);
      setConnectionController(null);
    }
  };

  const handleTableSelectionChange = (newSelectedTables: string[]) => {
    setSelectedTables(newSelectedTables);
    // If the currently previewed table is no longer selected, clear the preview
    if (selectedTable && !newSelectedTables.includes(selectedTable)) {
      setSelectedTable(null);
      setTableFields([]);
    }
  };

  const handleTableSelect = async (tableName: string) => {
    // Only allow selection of tables that are in the selected list
    if (!selectedTables.includes(tableName)) {
      toast.error('Please select this table first before previewing');
      return;
    }

    // Cancel any existing table loading
    if (connectionController) {
      connectionController.abort();
    }
    
    const controller = new AbortController();
    setConnectionController(controller);

    try {
      setSelectedTable(tableName);
      setLoading(true);
      
      toast.loading(`Loading schema for ${tableName}...`, { id: 'table-load' });

      const tableData = await fetchTableFields(tableName, controller.signal);
      setTableFields(tableData.fields);
      
      toast.dismiss('table-load');
      toast.success(`Loaded schema for ${tableName}`);
    } catch (error) {
      toast.dismiss('table-load');
      
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }
      
      console.error('Failed to fetch table schema:', error);
      toast.error('Failed to fetch table schema');
    } finally {
      setLoading(false);
      setConnectionController(null);
    }
  };

  const handleGenerateDescriptions = async (tableName: string, fields: TableField[]) => {
    try {
      setLoadingDescriptions(true);
      const response = await axios.post(`${API_URL}/api/database/describe`, {
        tableName,
        fields
      }, {
        timeout: 30000 // 30 second timeout
      });
      setTableFields(response.data.fields);
    } catch (error) {
      console.error('Failed to generate descriptions:', error);
      toast.error('Failed to generate field descriptions');
    } finally {
      setLoadingDescriptions(false);
    }
  };

  const fetchTableFields = async (tableName: string, signal?: AbortSignal): Promise<TableData> => {
    try {
      const schemaResponse = await axios.post(`${API_URL}/api/database/schema`, {
        ...config,
        tableName
      }, {
        timeout: 60000, // 60 second timeout
        signal
      });

      const tableDescription = schemaResponse.data.table_description;

      const fieldsResponse = await axios.post(`${API_URL}/api/database/describe`, {
        tableName,
        fields: schemaResponse.data.fields
      }, {
        timeout: 60000, // 60 second timeout
        signal
      });

      return {
        fields: fieldsResponse.data.fields,
        tableDescription
      };
    } catch (error) {
      console.error(`Failed to fetch fields for table ${tableName}:`, error);
      throw error;
    }
  };

  const handleImport = async () => {
    if (!importStartTime || !currentHistoryId) {
      toast.error('Import session not properly initialized');
      return;
    }

    if (!previewData || selectedTables.length === 0) {
      toast.error('Please select at least one table to import');
      return;
    }

    try {
      setLoading(true);
      
      toast.loading('Starting import process...', { id: 'import' });
      
      // Update history to show import in progress
      const inProgressItem = createHistoryItem(
        config,
        'in_progress',
        selectedTables.length,
        0,
        [],
        undefined,
        undefined
      );
      inProgressItem.id = currentHistoryId;
      saveConnectionHistory(inProgressItem);

      const createdDb = await api.createDatabase({
        source_id: config.source_id,
        name: config.database,
        description: config.description,
        type: config.type,
        platform: config.platform,
        location: config.location,
        version: config.version
      });

      let importedCount = 0;
      const failedTables: string[] = [];
      const totalTables = selectedTables.length;
      
      toast.dismiss('import');

      // Process tables in batches to avoid overwhelming the system
      const batchSize = 5;
      for (let i = 0; i < selectedTables.length; i += batchSize) {
        const batch = selectedTables.slice(i, i + batchSize);
        
        await Promise.allSettled(batch.map(async (tableName) => {
        try {
          toast.loading(`Importing ${tableName}... (${importedCount + 1}/${totalTables})`, { 
            id: `import-${tableName}` 
          });
          
          const { fields: tableFields, tableDescription } = await fetchTableFields(tableName);

          const createdTable = await api.createTable({
            database_id: createdDb.id,
            name: tableName,
            description: tableDescription
          });

          for (const field of tableFields) {
            await api.createField({
              table_id: createdTable.id,
              name: field.fieldName,
              type: field.dataType,
              description: field.description || `Field ${field.fieldName} in table ${tableName}`,
              nullable: field.isNullable === 'YES',
              is_primary_key: field.isPrimaryKey === 'YES',
              is_foreign_key: field.isForeignKey === 'YES',
              default_value: field.defaultValue
            });
          }

          importedCount++;
          
          toast.dismiss(`import-${tableName}`);
          toast.success(`Imported: ${tableName} (${importedCount}/${totalTables})`, {
            duration: 2000
          });
          
          // Update progress in history
          const progressItem = createHistoryItem(
            config,
            'in_progress',
            totalTables,
            importedCount,
            failedTables,
            undefined,
            undefined
          );
          progressItem.id = currentHistoryId;
          saveConnectionHistory(progressItem);
          
        } catch (error) {
          toast.dismiss(`import-${tableName}`);
          console.error(`Failed to import table ${tableName}:`, error);
          failedTables.push(tableName);
          toast.error(`Failed: ${tableName}`, { duration: 3000 });
        }
        }));
        
        // Small delay between batches to prevent overwhelming
        if (i + batchSize < selectedTables.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }

      // Final history update
      const finalStatus = failedTables.length === 0 ? 'success' : 
                         importedCount === 0 ? 'failed' : 'partial';
      
      const finalItem = createHistoryItem(
        config,
        finalStatus,
        totalTables,
        importedCount,
        failedTables,
        failedTables.length > 0 ? `${failedTables.length} tables failed to import` : undefined,
        Date.now() - importStartTime
      );
      finalItem.id = currentHistoryId;
      saveConnectionHistory(finalItem);

      if (importedCount > 0) {
        toast.success(`Successfully imported ${importedCount} tables to data dictionary`);
      }
      
      if (failedTables.length > 0) {
        toast.error(`${failedTables.length} tables failed to import`);
      }

      setConfig({
        server: '',
        database: '',
        username: '',
        password: '',
        schema: '',
        source_id: '',
        description: '',
        type: '',
        platform: '',
        location: '',
        version: ''
      });
      setPreviewData(null);
      setTableFields([]);
      setSelectedTables([]);
      setSelectedTable(null);
      setCurrentHistoryId(null);
      setImportStartTime(null);
      setStep('history');
    } catch (error) {
      console.error('Failed to import:', error);
      
      // Update history with failure
      if (currentHistoryId && importStartTime) {
        const failedItem = createHistoryItem(
          config,
          'failed',
          selectedTables.length,
          0,
          [],
          error instanceof Error ? error.message : 'Import failed',
          Date.now() - importStartTime
        );
        failedItem.id = currentHistoryId;
        saveConnectionHistory(failedItem);
      }
      
      toast.error('Failed to import database');
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (!config.source_id || !config.description || !config.type || !config.platform) {
      toast.error('Please fill in all database information fields');
      return;
    }
    setStep('credentials');
  };

  const handleReconnect = (historyConfig: any) => {
    // Cancel any existing connection
    if (connectionController) {
      connectionController.abort();
      setConnectionController(null);
    }
    
    setConfig(historyConfig);
    setStep('credentials');
    toast.success('Configuration loaded from history');
  };

  const handleResume = (historyItem: any) => {
    // Cancel any existing connection
    if (connectionController) {
      connectionController.abort();
      setConnectionController(null);
    }
    
    setConfig(historyItem.config);
    // You could implement logic here to resume from where it left off
    // For now, we'll just reconnect and let user select tables again
    setStep('credentials');
    toast.success('Resuming from previous session');
  };

  const handleNewConnection = () => {
    // Cancel any existing connection
    if (connectionController) {
      connectionController.abort();
      setConnectionController(null);
    }
    
    setConfig({
      server: '',
      database: '',
      username: '',
      password: '',
      schema: '',
      source_id: '',
      description: '',
      type: '',
      platform: '',
      location: '',
      version: ''
    });
    setPreviewData(null);
    setTableFields([]);
    setSelectedTables([]);
    setSelectedTable(null);
    setCurrentHistoryId(null);
    setImportStartTime(null);
    setStep('info');
  };

  const renderStepContent = () => {
    switch (step) {
      case 'history':
        return (
          <div className="space-y-6">
            <ConnectionHistory
              onReconnect={handleReconnect}
              onResume={handleResume}
              sources={sources}
            />
            <div className="flex justify-center">
              <button
                onClick={handleNewConnection}
                className="bg-[#003B7E] text-white px-6 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
              >
                New Connection
              </button>
            </div>
          </div>
        );
      case 'info':
        return (
          <DatabaseInfoForm
            config={config}
            sources={sources}
            onConfigChange={setConfig}
            onNext={handleNext}
          />
        );
      case 'credentials':
        return (
          <DatabaseCredentialsForm
            config={config}
            onConfigChange={setConfig}
            onBack={() => setStep('info')}
            onConnect={handleConnect}
            loading={loading}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/settings" className="text-[#003B7E] hover:text-[#002c5f] flex items-center">
            <ArrowLeft className="h-5 w-5 mr-1" />
            Back to Settings
          </Link>
          <h1 className="text-2xl font-bold">Database Import</h1>
        </div>
        {step !== 'history' && (
          <button
            onClick={() => setStep('history')}
            className="text-[#003B7E] hover:text-[#002c5f] text-sm px-3 py-1 border border-[#003B7E] rounded-lg hover:bg-blue-50 transition-colors"
          >
            View History
          </button>
        )}
      </div>

      {/* Session Status */}
      {previewData && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-blue-900">Active Import Session</h3>
              <p className="text-sm text-blue-700">
                Connected to {config.database} ({config.type}) - {previewData.tables.length} tables available
              </p>
            </div>
            <div className="text-sm text-blue-600">
              {selectedTables.length} selected for import
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Connection Panel */}
        <div className={`${step === 'history' ? 'col-span-12' : 'col-span-4'} bg-white rounded-lg shadow-md p-6`}>
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Database className="h-5 w-5 mr-2" />
            {step === 'history' ? 'Connection History' : 
             step === 'info' ? 'Database Information' : 'Connection Details'}
          </h2>
          
          {step === 'history' ? (
            renderStepContent()
          ) : (
            <div className="space-y-4">
              {renderStepContent()}
            </div>
          )}
        </div>

        {/* Schema Preview */}
        {step !== 'history' && (
          <div className="col-span-8 bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Schema Preview</h2>
          </div>

          <SchemaPreview
            previewData={previewData}
            config={config}
            sources={sources}
            selectedTable={selectedTable}
            selectedTables={selectedTables}
            tableFields={tableFields}
            loading={loading}
            loadingDescriptions={loadingDescriptions}
            onTableSelect={handleTableSelect}
            onTableSelectionChange={handleTableSelectionChange}
            onImport={handleImport}
          />
        </div>
        )}
      </div>
    </div>
  );
}