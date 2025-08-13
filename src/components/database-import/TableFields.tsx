import React from 'react';
import { Loader2 } from 'lucide-react';

interface TableFieldsProps {
  tableName: string;
  fields: any[];
  loadingDescriptions: boolean;
}

export default function TableFields({
  tableName,
  fields,
  loadingDescriptions,
}: TableFieldsProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <h4 className="font-medium text-gray-900 flex items-center">
          Table: {tableName}
          {loadingDescriptions && (
            <Loader2 className="h-4 w-4 ml-2 animate-spin text-[#003B7E]" />
          )}
        </h4>
        <p className="text-sm text-gray-500 mt-1">
          {fields.length} field{fields.length !== 1 ? 's' : ''}
        </p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Field Name
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Data Type
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nullable
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Keys
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Default
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {fields.map((field, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-sm font-medium text-gray-900">
                  {field.fieldName}
                </td>
                <td className="px-4 py-2 text-sm text-gray-500">
                  {field.dataType}
                </td>
                <td className="px-4 py-2 text-sm text-gray-500">
                  <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                    field.isNullable === 'YES' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {field.isNullable === 'YES' ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm">
                  <div className="flex space-x-1">
                    {field.isPrimaryKey === 'YES' && (
                      <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        PK
                      </span>
                    )}
                    {field.isForeignKey === 'YES' && (
                      <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                        FK
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2 text-sm text-gray-500">
                  {field.defaultValue || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}