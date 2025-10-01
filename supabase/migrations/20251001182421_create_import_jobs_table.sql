-- Create Import Jobs Table
-- 
-- 1. New Tables
--    - import_jobs: Tracks background import job status
--      - id (uuid, primary key) - Unique identifier for the import job
--      - user_id (uuid) - Reference to auth.users who started the job
--      - config (jsonb) - Database connection configuration
--      - status (text) - Job status: pending, in_progress, completed, failed, cancelled
--      - total_tables (integer) - Total number of tables to import
--      - imported_tables (integer) - Number of tables successfully imported
--      - failed_tables (text[]) - Array of failed table names
--      - error_message (text) - Error details if failed
--      - database_id (uuid) - Created database ID (if successful)
--      - created_at (timestamptz) - When the job was created
--      - updated_at (timestamptz) - Last update timestamp
--      - completed_at (timestamptz) - When the job finished
-- 
-- 2. Security
--    - Enable RLS on import_jobs table
--    - Add policies for users to manage their own jobs
-- 
-- 3. Indexes
--    - Index on user_id for fast lookups
--    - Index on status for filtering active jobs

CREATE TABLE IF NOT EXISTS import_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  config jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
  total_tables integer NOT NULL DEFAULT 0,
  imported_tables integer NOT NULL DEFAULT 0,
  failed_tables text[] DEFAULT '{}',
  error_message text,
  database_id uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Enable RLS
ALTER TABLE import_jobs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own import jobs
CREATE POLICY "Users can view own import jobs"
  ON import_jobs
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Policy: Users can create their own import jobs
CREATE POLICY "Users can create own import jobs"
  ON import_jobs
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own import jobs
CREATE POLICY "Users can update own import jobs"
  ON import_jobs
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_import_jobs_user_id ON import_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_import_jobs_status ON import_jobs(status);
CREATE INDEX IF NOT EXISTS idx_import_jobs_created_at ON import_jobs(created_at DESC);