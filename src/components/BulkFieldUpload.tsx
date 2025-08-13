import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileJson, FileUp } from 'lucide-react';
import { toast } from 'react-hot-toast';
import * as api from '../lib/api';

interface BulkFieldUploadProps {
  selectedSourceId: string;
  selectedDatabaseId: string;
  onSuccess: () => void;
}

export default function BulkFieldUpload({ 
  selectedSourceId, 
  selectedDatabaseId,
  onSuccess 
}: BulkFieldUploadProps) {
  const [loading, setLoading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!selectedDatabaseId) {
      toast.error('Please select a database first');
      return;
    }

    const file = acceptedFiles[0];
    if (!file) return;

    try {
      setLoading(true);
      const fields = await api.parseFieldsFile(file);
      const createdFields = await api.createFieldsBulk(selectedDatabaseId, fields);
      toast.success(`Successfully created ${createdFields.length} fields`);
      onSuccess();
    } catch (error) {
      console.error('Error processing file:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to process file');
    } finally {
      setLoading(false);
    }
  }, [selectedDatabaseId, onSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    multiple: false,
    disabled: !selectedDatabaseId || loading
  });

  return (
    <div className="space-y-8">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-[#003B7E] bg-[#003B7E]/5' : 'border-gray-300'
        } ${!selectedDatabaseId || loading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} disabled={!selectedDatabaseId || loading} />
        <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
        <p className="text-lg mb-2">
          {loading ? 'Uploading...' : selectedDatabaseId
            ? 'Drag & drop your fields file here, or click to select'
            : 'Please select a database first'}
        </p>
        <p className="text-sm text-gray-500">
          Supported formats: .csv, .json, .xlsx
        </p>
      </div>

      <div className="mt-8">
        <h4 className="font-medium mb-4">File Format Examples:</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <FileJson className="h-5 w-5 text-[#003B7E]" />
              <span className="font-medium">JSON Format</span>
            </div>
            <pre className="text-sm overflow-x-auto">
{`[
  {
    "table_name": "customers",
    "table_description": "Customer table",
    "name": "id",
    "type": "uuid",
    "description": "Primary key",
    "nullable": false,
    "is_primary_key": true
  }
]`}
            </pre>
          </div>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <FileUp className="h-5 w-5 text-[#003B7E]" />
              <span className="font-medium">CSV Format</span>
            </div>
            <pre className="text-sm overflow-x-auto">
{`Table Name,Table Description,Field Name,Data Type,Description,Nullable,Primary Key,Foreign Key,Default Value
customers,Customer table,id,uuid,Primary key,No,Yes,No,
customers,Customer table,email,varchar(255),Email address,No,No,No,
orders,Order table,id,uuid,Primary key,No,Yes,No,
orders,Order table,customer_id,uuid,Customer reference,No,No,Yes,`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}