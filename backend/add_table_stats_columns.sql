-- Add record_count and last_imported columns to tables table
ALTER TABLE tables ADD record_count INT NULL;
ALTER TABLE tables ADD last_imported DATETIME NULL;
