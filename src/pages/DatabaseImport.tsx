import React, { useState, useEffect } from 'react';
import { ArrowLeft, Database } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import * as api from '../lib/api';
import DatabaseInfoForm from '../components/database-import/DatabaseInfoForm';
import DatabaseCredentialsForm from '../components/database-import/DatabaseCredentialsForm';
import SchemaPreview from '../components/database-import/SchemaPreview';

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
  const [step, setStep] = useState<'info' | 'credentials'>('info');
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
  const [tableFields, setTableFields] = useState<TableField[]>([]);

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
  }, []);

  const handleConnect = async () => {
    if (!config.source_id) {
      toast.error('Please select a source system');
      return;
    }

    if (!config.server || !config.database || !config.username || !config.password) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/api/database/connect`, config);
      setPreviewData(response.data);
      toast.success('Successfully connected to database');
    } catch (error) {
      console.error('Failed to connect:', error);
      toast.error('Failed to connect to database');
    } finally {
      setLoading(false);
    }
  };

  const handleTableSelect = async (tableName: string) => {
    try {
      setSelectedTable(tableName);
      setLoading(true);

      const tableData = await fetchTableFields(tableName);
      setTableFields(tableData.fields);
    } catch (error) {
      console.error('Failed to fetch table schema:', error);
      toast.error('Failed to fetch table schema');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDescriptions = async (tableName: string, fields: TableField[]) => {
    try {
      setLoadingDescriptions(true);
      const response = await axios.post(`${API_URL}/api/database/describe`, {
        tableName,
        fields
      });
      setTableFields(response.data.fields);
    } catch (error) {
      console.error('Failed to generate descriptions:', error);
      toast.error('Failed to generate field descriptions');
    } finally {
      setLoadingDescriptions(false);
    }
  };

  const fetchTableFields = async (tableName: string): Promise<TableData> => {
    try {
      const schemaResponse = await axios.post(`${API_URL}/api/database/schema`, {
        ...config,
        tableName
      });

      const tableDescription = schemaResponse.data.table_description;

      const fieldsResponse = await axios.post(`${API_URL}/api/database/describe`, {
        tableName,
        fields: schemaResponse.data.fields
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
    if (!previewData) {
      toast.error('No data to import');
      return;
    }

    try {
      setLoading(true);

      const createdDb = await api.createDatabase({
        source_id: config.source_id,
        name: config.database,
        description: config.description,
        type: config.type,
        platform: config.platform,
        location: config.location,
        version: config.version
      });

      for (const tableName of previewData.tables) {
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

        toast.success(`Imported table: ${tableName}`);
      }

      toast.success('Successfully imported database to data dictionary');

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
      setSelectedTable(null);
      setStep('info');
    } catch (error) {
      console.error('Failed to import:', error);
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
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Connection Panel */}
        <div className="col-span-4 bg-white rounded-lg shadow-md p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Database className="h-5 w-5 mr-2" />
            {step === 'info' ? 'Database Information' : 'Connection Details'}
          </h2>
          
          <div className="space-y-4">
            {step === 'info' ? (
              <DatabaseInfoForm
                config={config}
                sources={sources}
                onConfigChange={setConfig}
                onNext={handleNext}
              />
            ) : (
              <DatabaseCredentialsForm
                config={config}
                onConfigChange={setConfig}
                onBack={() => setStep('info')}
                onConnect={handleConnect}
                loading={loading}
              />
            )}
          </div>
        </div>

        {/* Schema Preview */}
        <div className="col-span-8 bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Schema Preview</h2>
          </div>

          <SchemaPreview
            previewData={previewData}
            config={config}
            sources={sources}
            selectedTable={selectedTable}
            tableFields={tableFields}
            loading={loading}
            loadingDescriptions={loadingDescriptions}
            onTableSelect={handleTableSelect}
            onImport={handleImport}
          />
        </div>
      </div>
    </div>
  );
}