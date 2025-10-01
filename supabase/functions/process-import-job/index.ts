import { createClient } from 'npm:@supabase/supabase-js@2.39.7';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Client-Info, Apikey',
};

interface ImportJobRequest {
  job_id: string;
  config: any;
  selected_tables: string[];
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const { job_id, config, selected_tables } = await req.json() as ImportJobRequest;

    // Update job status to in_progress
    await supabase
      .from('import_jobs')
      .update({ 
        status: 'in_progress',
        updated_at: new Date().toISOString(),
        total_tables: selected_tables.length 
      })
      .eq('id', job_id);

    // Process in background using EdgeRuntime.waitUntil
    const processJob = async () => {
      try {
        const backendUrl = 'http://10.24.37.99:8000';
        let importedCount = 0;
        const failedTables: string[] = [];
        let createdDbId: string | null = null;

        // Create database
        try {
          const dbResponse = await fetch(`${backendUrl}/databases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              source_id: config.source_id,
              name: config.database,
              description: config.description,
              type: config.type,
              platform: config.platform,
              location: config.location,
              version: config.version,
            }),
          });

          if (!dbResponse.ok) {
            throw new Error('Failed to create database');
          }

          const createdDb = await dbResponse.json();
          createdDbId = createdDb.id;
        } catch (error) {
          await supabase
            .from('import_jobs')
            .update({
              status: 'failed',
              error_message: 'Failed to create database: ' + error.message,
              updated_at: new Date().toISOString(),
              completed_at: new Date().toISOString(),
            })
            .eq('id', job_id);
          return;
        }

        // Process tables
        for (const tableName of selected_tables) {
          try {
            // Check if job was cancelled
            const { data: jobData } = await supabase
              .from('import_jobs')
              .select('status')
              .eq('id', job_id)
              .single();

            if (jobData?.status === 'cancelled') {
              return;
            }

            // Fetch table schema
            const schemaResponse = await fetch(`${backendUrl}/api/database/schema`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ...config, tableName }),
            });

            if (!schemaResponse.ok) {
              throw new Error('Failed to fetch schema');
            }

            const schemaData = await schemaResponse.json();

            // Generate descriptions
            const descResponse = await fetch(`${backendUrl}/api/database/describe`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                tableName,
                fields: schemaData.fields,
              }),
            });

            if (!descResponse.ok) {
              throw new Error('Failed to generate descriptions');
            }

            const { fields } = await descResponse.json();
            const tableDescription = schemaData.table_description;

            // Create table
            const tableResponse = await fetch(`${backendUrl}/tables`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                database_id: createdDbId,
                name: tableName,
                description: tableDescription || `Stores ${tableName.replace('_', ' ').toLowerCase()} data`,
              }),
            });

            if (!tableResponse.ok) {
              throw new Error('Failed to create table');
            }

            const createdTable = await tableResponse.json();

            // Create fields
            for (const field of fields) {
              await fetch(`${backendUrl}/fields`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  table_id: createdTable.id,
                  name: field.fieldName,
                  type: field.dataType,
                  description: field.description || `${field.fieldName.replace('_', ' ')} data`,
                  nullable: field.isNullable === 'YES',
                  is_primary_key: field.isPrimaryKey === 'YES',
                  is_foreign_key: field.isForeignKey === 'YES',
                  default_value: field.defaultValue,
                }),
              });
            }

            importedCount++;

            // Update progress
            await supabase
              .from('import_jobs')
              .update({
                imported_tables: importedCount,
                updated_at: new Date().toISOString(),
              })
              .eq('id', job_id);
          } catch (error) {
            failedTables.push(tableName);
            await supabase
              .from('import_jobs')
              .update({
                failed_tables: failedTables,
                updated_at: new Date().toISOString(),
              })
              .eq('id', job_id);
          }
        }

        // Update final status
        const finalStatus = failedTables.length === 0 ? 'completed' :
                           importedCount === 0 ? 'failed' : 'completed';

        await supabase
          .from('import_jobs')
          .update({
            status: finalStatus,
            imported_tables: importedCount,
            failed_tables: failedTables,
            database_id: createdDbId,
            error_message: failedTables.length > 0 ? `${failedTables.length} tables failed` : null,
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          })
          .eq('id', job_id);
      } catch (error) {
        await supabase
          .from('import_jobs')
          .update({
            status: 'failed',
            error_message: error.message,
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          })
          .eq('id', job_id);
      }
    };

    // Start background processing
    processJob();

    return new Response(
      JSON.stringify({ success: true, message: 'Import job started' }),
      {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    );
  }
});