import React from 'react';
import { SourceSystem } from '../../lib/api';

interface DatabaseInfoFormProps {
  config: {
    source_id: string;
    description: string;
    type: string;
    platform: string;
    location: string;
    version: string;
  };
  sources: SourceSystem[];
  onConfigChange: (config: any) => void;
  onNext: () => void;
}

export default function DatabaseInfoForm({
  config,
  sources,
  onConfigChange,
  onNext
}: DatabaseInfoFormProps) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Source System *
        </label>
        <select
          value={config.source_id}
          onChange={(e) => onConfigChange({ ...config, source_id: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
        >
          <option value="">Select Source System</option>
          {sources.map((source) => (
            <option key={source.id} value={source.id}>
              {source.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description *
        </label>
        <input
          type="text"
          value={config.description}
          onChange={(e) => onConfigChange({ ...config, description: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder="Brief description of the database"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Type *
        </label>
        <input
          type="text"
          value={config.type}
          onChange={(e) => onConfigChange({ ...config, type: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder="e.g., SQL Server, Oracle"
          list="database-types"
        />
        <datalist id="database-types">
          <option value="MSSQL" />
          <option value="Oracle" />
          <option value="PostgreSQL" />
          <option value="MySQL" />
        </datalist>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Platform *
        </label>
        <input
          type="text"
          value={config.platform}
          onChange={(e) => onConfigChange({ ...config, platform: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder="e.g., Windows, Linux"
          list="platforms"
        />
        <datalist id="platforms">
          <option value="Windows" />
          <option value="Linux" />
          <option value="macOS" />
          <option value="Cloud" />
        </datalist>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Location
        </label>
        <input
          type="text"
          value={config.location}
          onChange={(e) => onConfigChange({ ...config, location: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder="e.g., Data Center A"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Version
        </label>
        <input
          type="text"
          value={config.version}
          onChange={(e) => onConfigChange({ ...config, version: e.target.value })}
          className="w-full rounded-lg border border-gray-300 px-4 py-2"
          placeholder="e.g., 2019"
        />
      </div>

      <button
        onClick={onNext}
        className="w-full bg-[#003B7E] text-white px-4 py-2 rounded-lg hover:bg-[#002c5f] transition-colors"
      >
        Next: Connection Details
      </button>
    </>
  );
}