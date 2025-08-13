export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      source_systems: {
        Row: {
          id: string
          name: string
          description: string | null
          category: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          name: string
          description?: string | null
          category?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          name?: string
          description?: string | null
          category?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      databases: {
        Row: {
          id: string
          source_id: string
          name: string
          description: string | null
          type: string | null
          platform: string | null
          location: string | null
          version: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          source_id: string
          name: string
          description?: string | null
          type?: string | null
          platform?: string | null
          location?: string | null
          version?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          source_id?: string
          name?: string
          description?: string | null
          type?: string | null
          platform?: string | null
          location?: string | null
          version?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      tables: {
        Row: {
          id: string
          database_id: string
          category_id: string | null
          name: string
          description: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          database_id: string
          category_id?: string | null
          name: string
          description?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          database_id?: string
          category_id?: string | null
          name?: string
          description?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      fields: {
        Row: {
          id: string
          table_id: string
          name: string
          type: string
          description: string | null
          nullable: boolean
          is_primary_key: boolean
          is_foreign_key: boolean
          default_value: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          table_id: string
          name: string
          type: string
          description?: string | null
          nullable?: boolean
          is_primary_key?: boolean
          is_foreign_key?: boolean
          default_value?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          table_id?: string
          name?: string
          type?: string
          description?: string | null
          nullable?: boolean
          is_primary_key?: boolean
          is_foreign_key?: boolean
          default_value?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      categories: {
        Row: {
          id: string
          name: string
          description: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          name: string
          description?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          name?: string
          description?: string | null
          created_at?: string
          updated_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}