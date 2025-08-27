import React from 'react';
import { RefreshCw } from 'lucide-react';

interface DatabaseCredentialsFormProps {
  config: {
    server: string;
    database: string;
    username: string;
    password: string;
    schema?: string;
    type: string;
  };
  onConfigChange: (config: any) => void;
  onBack: () => void;
  onConnect: () => void;
  loading: boolean;
}

const DATABASE_TYPES = {
  MSSQL: {
    serverPlaceholder: 'e.g., 10.24.37.99 or server\\instance',
    databasePlaceholder: 'e.g., DATA-DICTIONARY',
    usernamePlaceholder: 'e.g., bk-pay',
    connectionFormat: 'Server=server;Database=dbname;User Id=username;Password=password;'
  },
  Oracle: {
    serverPlaceholder: 'e.g., localhost:1521 or server.domain.com',
    databasePlaceholder: 'e.g., ORCL or service_name',
    usernamePlaceholder: 'e.g., system',
    schemaPlaceholder: 'e.g., T24, HR (optional)',
    connectionFormat: 'username/password@server/service_name'
  },
  PostgreSQL: {
    serverPlaceholder: 'e.g., localhost or db.domain.com',
    databasePlaceholder: 'e.g., postgres',
    usernamePlaceholder: 'e.g., postgres',
    connectionFormat: 'host=server port=5432 dbname=database user=username password=password'
  },
  MySQL: {
    serverPlaceholder: 'e.g., localhost:3306 or db.domain.com',
    databasePlaceholder: 'e.g., mydatabase',
    usernamePlaceholder: 'e.g., root',
    connectionFormat: 'mysql://username:password@server:3306/database'
  }
};

export default function DatabaseCredentialsForm({
  config,
  onConfigChange,
  onBack,
  onConnect,
  loading
}: DatabaseCredentialsFormProps) {
  const dbTypeConfig = DATABASE_TYPES[config.type as keyof typeof DATABASE_TYPES] || DATABASE_TYPES.MSSQL;

  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Server *
        </label>
        <input
          type="text"
          value={config.server}
          onChange={(e) => onConfigChange({ ...config, server: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder={dbTypeConfig.serverPlaceholder}
        />
        <p className="mt-1 text-xs text-gray-500">
          {config.type === 'MSSQL' && 'For named instances, use server\\instance format'}
          {config.type === 'Oracle' && 'Include port if not using default (1521)'}
          {config.type === 'PostgreSQL' && 'Default port is 5432 if not specified'}
          {config.type === 'MySQL' && 'Default port is 3306 if not specified'}
        </p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Database Name *
        </label>
        <input
          type="text"
          value={config.database}
          onChange={(e) => onConfigChange({ ...config, database: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder={dbTypeConfig.databasePlaceholder}
        />
        <p className="mt-1 text-xs text-gray-500">
          {config.type === 'Oracle' && 'This is your Oracle service name or SID'}
          {config.type === 'PostgreSQL' && 'The name of the PostgreSQL database'}
          {config.type === 'MySQL' && 'The name of the MySQL database'}
        </p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Username *
        </label>
        <input
          type="text"
          value={config.username}
          onChange={(e) => onConfigChange({ ...config, username: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder={dbTypeConfig.usernamePlaceholder}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Password *
        </label>
        <input
          type="password"
          value={config.password}
          onChange={(e) => onConfigChange({ ...config, password: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
        />
      </div>

      {config.type === 'Oracle' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Schema
          </label>
          <input
            type="text"
            value={config.schema || ''}
            onChange={(e) => onConfigChange({ ...config, schema: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-4 py-2"
            placeholder={dbTypeConfig.schemaPlaceholder}
          />
          <p className="mt-1 text-xs text-gray-500">
            Optional: Specify schema name (e.g., T24) to access specific schema objects
          </p>
        </div>
      )}

      <div className="bg-gray-50 p-4 rounded-lg mt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Connection Format</h4>
        <p className="text-xs text-gray-600 font-mono">
          {dbTypeConfig.connectionFormat}
        </p>
      </div>

      <div className="flex space-x-2">
        <button
          onClick={onBack}
          className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
        >
          Back
        </button>
        <button
          onClick={onConnect}
          disabled={loading}
          className="flex-1 bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors disabled:opacity-50 flex items-center justify-center"
        >
          {loading ? (
            <>
              <RefreshCw className="h-5 w-5 animate-spin mr-2" />
              <span>Connecting...</span>
            </>
          ) : (
            'Connect'
          )}
        </button>
      </div>
    </>
  );
}