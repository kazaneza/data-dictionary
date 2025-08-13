import axios from 'axios';
import { toast } from 'react-hot-toast';
import * as XLSX from 'xlsx';

// Cache configuration
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const cache = new Map<string, { data: any; timestamp: number }>();

const api = axios.create({
  baseURL: 'http://10.24.37.99:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // Increased timeout
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    if (!error.response) {
      console.error('Network Error Details:', error);
      toast.error('Cannot connect to the server. Please ensure the backend is running.');
      return Promise.reject(error);
    }

    // Handle authentication errors
    if (error.response.status === 401 || error.response.status === 403) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('userRole');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // Retry logic for 500 errors
    if (error.response.status === 500 && error.config && !error.config.__isRetryRequest) {
      error.config.__isRetryRequest = true;
      return api(error.config);
    }

    if (error.response.status === 422) {
      const validationErrors = error.response.data.detail;
      if (Array.isArray(validationErrors)) {
        validationErrors.forEach((err: any) => {
          toast.error(`Validation error: ${err.msg}`);
        });
      } else {
        toast.error('Invalid data provided. Please check your input.');
      }
      return Promise.reject(error);
    }

    switch (error.response.status) {
      case 404:
        toast.error('Resource not found');
        break;
      case 500:
        toast.error('Server error. Please try again later.');
        break;
      default:
        const message = error.response?.data?.detail || 'An error occurred';
        toast.error(message);
    }

    return Promise.reject(error);
  }
);

// Cache helper functions
const getCached = <T>(key: string): T | null => {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data as T;
  }
  return null;
};

const setCache = (key: string, data: any) => {
  cache.set(key, { data, timestamp: Date.now() });
};

const clearCache = () => {
  cache.clear();
};

// Batch loading helper
const batchLoad = async <T>(
  items: string[],
  loadFn: (item: string) => Promise<T>,
  batchSize = 5
): Promise<T[]> => {
  const results: T[] = [];
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    const batchResults = await Promise.all(
      batch.map(item => loadFn(item).catch(error => {
        console.error(`Error loading item ${item}:`, error);
        return null;
      }))
    );
    results.push(...batchResults.filter(Boolean));
  }
  return results;
};

// API Functions with caching and optimizations
export const fetchDashboardStats = async () => {
  const cached = getCached<any>('dashboardStats');
  if (cached) return cached;

  const response = await api.get('/dashboard/stats');
  setCache('dashboardStats', response.data);
  return response.data;
};

// Types
export interface SourceSystem {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

export interface Database {
  id: string;
  source_id: string;
  name: string;
  description?: string;
  type?: string;
  platform?: string;
  location?: string;
  version?: string;
}

export interface Table {
  id: string;
  database_id: string;
  category_id?: string;
  name: string;
  description?: string;
}

export interface Field {
  id: string;
  table_id: string;
  name: string;
  type: string;
  description?: string;
  nullable?: boolean;
  is_primary_key?: boolean;
  is_foreign_key?: boolean;
  default_value?: string;
}

export interface Category {
  id: string;
  name: string;
  description?: string;
}

// Source Systems
export const fetchSources = async (): Promise<SourceSystem[]> => {
  const cached = getCached<SourceSystem[]>('sources');
  if (cached) return cached;

  const response = await api.get('/sources');
  setCache('sources', response.data);
  return response.data;
};

export const createSource = async (data: Omit<SourceSystem, 'id'>): Promise<SourceSystem> => {
  const response = await api.post('/sources', data);
  invalidateCache('sources');
  return response.data;
};

export const updateSource = async (id: string, data: Partial<SourceSystem>): Promise<SourceSystem> => {
  const response = await api.put(`/sources/${id}`, data);
  invalidateCache('sources');
  return response.data;
};

export const deleteSource = async (id: string): Promise<void> => {
  await api.delete(`/sources/${id}`);
  invalidateCache('sources');
};

// Databases with pagination
export const fetchDatabases = async (page = 1, limit = 50): Promise<Database[]> => {
  const cacheKey = `databases_${page}_${limit}`;
  const cached = getCached<Database[]>(cacheKey);
  if (cached) return cached;

  const response = await api.get('/databases', {
    params: { page, limit }
  });
  setCache(cacheKey, response.data);
  return response.data;
};

export const createDatabase = async (data: Omit<Database, 'id'>): Promise<Database> => {
  const response = await api.post('/databases', data);
  invalidateCache('databases');
  return response.data;
};

export const updateDatabase = async (id: string, data: Partial<Database>): Promise<Database> => {
  const response = await api.put(`/databases/${id}`, data);
  invalidateCache('databases');
  return response.data;
};

export const deleteDatabase = async (id: string): Promise<void> => {
  await api.delete(`/databases/${id}`);
  invalidateCache('databases');
};

// Tables with pagination and filtering
export const fetchTables = async (
  databaseId?: string,
  page = 1,
  limit = 50
): Promise<Table[]> => {
  const cacheKey = `tables_${databaseId || 'all'}_${page}_${limit}`;
  const cached = getCached<Table[]>(cacheKey);
  if (cached) return cached;

  const response = await api.get('/tables', {
    params: { database_id: databaseId, page, limit }
  });
  setCache(cacheKey, response.data);
  return response.data;
};

export const createTable = async (data: Omit<Table, 'id'>): Promise<Table> => {
  const response = await api.post('/tables', data);
  invalidateCache('tables');
  return response.data;
};

export const updateTable = async (id: string, data: Partial<Table>): Promise<Table> => {
  const response = await api.put(`/tables/${id}`, data);
  invalidateCache('tables');
  return response.data;
};

export const deleteTable = async (id: string): Promise<void> => {
  await api.delete(`/tables/${id}`);
  invalidateCache('tables');
};

// Fields with pagination and lazy loading
export const fetchFields = async (
  tableId?: string,
  page = 1,
  limit = 100
): Promise<Field[]> => {
  const cacheKey = `fields_${tableId || 'all'}_${page}_${limit}`;
  const cached = getCached<Field[]>(cacheKey);
  if (cached) return cached;

  const response = await api.get('/fields', {
    params: { table_id: tableId, page, limit }
  });
  setCache(cacheKey, response.data);
  return response.data;
};

export const createField = async (data: Omit<Field, 'id'>): Promise<Field> => {
  const response = await api.post('/fields', data);
  invalidateCache('fields');
  return response.data;
};

export const updateField = async (id: string, data: Partial<Field>): Promise<Field> => {
  const response = await api.put(`/fields/${id}`, data);
  invalidateCache('fields');
  return response.data;
};

export const deleteField = async (id: string): Promise<void> => {
  await api.delete(`/fields/${id}`);
  invalidateCache('fields');
};

// Categories
export const fetchCategories = async (): Promise<Category[]> => {
  const cached = getCached<Category[]>('categories');
  if (cached) return cached;

  const response = await api.get('/categories');
  setCache('categories', response.data);
  return response.data;
};

export const createCategory = async (data: Omit<Category, 'id'>): Promise<Category> => {
  const response = await api.post('/categories', data);
  invalidateCache('categories');
  return response.data;
};

export const updateCategory = async (id: string, data: Partial<Category>): Promise<Category> => {
  const response = await api.put(`/categories/${id}`, data);
  invalidateCache('categories');
  return response.data;
};

export const deleteCategory = async (id: string): Promise<void> => {
  await api.delete(`/categories/${id}`);
  invalidateCache('categories');
};

// Cache management
export const invalidateCache = (key?: string) => {
  if (key) {
    const pattern = new RegExp(key);
    for (const cacheKey of cache.keys()) {
      if (pattern.test(cacheKey)) {
        cache.delete(cacheKey);
      }
    }
  } else {
    clearCache();
  }
};

export const login = async (username: string, password: string) => {
  const response = await api.post('/auth/login', { username, password });
  const { token, role } = response.data;
  localStorage.setItem('authToken', token);
  localStorage.setItem('userRole', role);
  return { token, role };
};

export const isAdmin = () => {
  return localStorage.getItem('userRole') === 'admin';
};

export const hasManageAccess = () => {
  const role = localStorage.getItem('userRole');
  return role === 'admin' || role === 'manager';
};

// File Parsing Functions
export interface BulkTableUpload {
  name: string;
  description?: string;
  category_id?: string;
}

export interface BulkFieldUpload {
  table_name: string;
  table_description?: string;
  name: string;
  type: string;
  description?: string;
  nullable?: boolean;
  is_primary_key?: boolean;
  is_foreign_key?: boolean;
  default_value?: string;
}

export const parseTablesFile = (file: File): Promise<BulkTableUpload[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        if (file.name.endsWith('.json')) {
          const data = JSON.parse(e.target?.result as string);
          resolve(data);
        } else if (file.name.endsWith('.csv') || file.name.endsWith('.xlsx')) {
          const data = e.target?.result;
          const workbook = XLSX.read(data, { type: 'binary' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { raw: false });
          
          const tables: BulkTableUpload[] = jsonData.map((row: any) => {
            const tableName = row['Table Name'] || row['TableName'] || row['table_name'] || row['name'];
            const description = row['Description'] || row['description'];
            const categoryId = row['Category ID'] || row['CategoryID'] || row['category_id'];

            if (!tableName) {
              throw new Error('Missing required field: Table Name');
            }

            return {
              name: tableName,
              description: description || undefined,
              category_id: categoryId || undefined
            };
          });
          
          if (tables.length === 0) {
            throw new Error('No valid tables found in the file');
          }
          
          resolve(tables);
        } else {
          reject(new Error('Unsupported file format'));
        }
      } catch (error) {
        if (error instanceof Error) {
          reject(new Error(`Failed to parse file: ${error.message}`));
        } else {
          reject(new Error('Failed to parse file'));
        }
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };
    
    if (file.name.endsWith('.json')) {
      reader.readAsText(file);
    } else {
      reader.readAsBinaryString(file);
    }
  });
};

export const parseFieldsFile = (file: File): Promise<BulkFieldUpload[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        if (file.name.endsWith('.json')) {
          const data = JSON.parse(e.target?.result as string);
          resolve(data);
        } else if (file.name.endsWith('.csv') || file.name.endsWith('.xlsx')) {
          const data = e.target?.result;
          const workbook = XLSX.read(data, { type: 'binary' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { raw: false });
          
          const fields: BulkFieldUpload[] = jsonData.map((row: any) => {
            const tableName = row['Table Name'] || row['TableName'] || row['table_name'];
            const tableDescription = row['Table Description'] || row['TableDescription'] || row['table_description'];
            const fieldName = row['Field Name'] || row['FieldName'] || row['field_name'];
            const dataType = row['Data Type'] || row['DataType'] || row['data_type'] || row['type'];
            const description = row['Description'] || row['description'];
            const nullable = row['Nullable'] || row['nullable'];
            const primaryKey = row['Primary Key'] || row['PrimaryKey'] || row['primary_key'] || row['is_primary_key'];
            const foreignKey = row['Foreign Key'] || row['ForeignKey'] || row['foreign_key'] || row['is_foreign_key'];
            const defaultValue = row['Default Value'] || row['DefaultValue'] || row['default_value'];

            if (!tableName || !fieldName || !dataType) {
              throw new Error('Missing required fields: Table Name, Field Name, or Data Type');
            }

            return {
              table_name: tableName,
              table_description: tableDescription || undefined,
              name: fieldName,
              type: dataType,
              description: description || undefined,
              nullable: nullable?.toLowerCase() === 'yes' || nullable === 'true' || nullable === true,
              is_primary_key: primaryKey?.toLowerCase() === 'yes' || primaryKey === 'true' || primaryKey === true,
              is_foreign_key: foreignKey?.toLowerCase() === 'yes' || foreignKey === 'true' || foreignKey === true,
              default_value: defaultValue || undefined
            };
          });
          
          if (fields.length === 0) {
            throw new Error('No valid fields found in the file');
          }
          
          resolve(fields);
        } else {
          reject(new Error('Unsupported file format'));
        }
      } catch (error) {
        if (error instanceof Error) {
          reject(new Error(`Failed to parse file: ${error.message}`));
        } else {
          reject(new Error('Failed to parse file'));
        }
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };
    
    if (file.name.endsWith('.json')) {
      reader.readAsText(file);
    } else {
      reader.readAsBinaryString(file);
    }
  });
};