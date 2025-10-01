import { useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { toast } from 'react-hot-toast';

interface ImportJob {
  id: string;
  user_id: string;
  config: any;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  total_tables: number;
  imported_tables: number;
  failed_tables: string[];
  error_message: string | null;
  database_id: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export function useImportJob() {
  const [activeJob, setActiveJob] = useState<ImportJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);
  const authListenerRef = useRef<any>(null);

  // Check for active import jobs when component mounts or user logs in
  const checkForActiveJobs = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();

      if (!user) return;

      // Find any in-progress or pending jobs for this user
      const { data: jobs, error } = await supabase
        .from('import_jobs')
        .select('*')
        .eq('user_id', user.id)
        .in('status', ['pending', 'in_progress'])
        .order('created_at', { ascending: false })
        .limit(1);

      if (error) {
        console.error('Failed to check for active jobs:', error);
        return;
      }

      if (jobs && jobs.length > 0) {
        const job = jobs[0] as ImportJob;
        setActiveJob(job);
        setIsPolling(true);
        toast('Resuming import job...', { duration: 2000 });
      }
    } catch (error) {
      console.error('Error checking for active jobs:', error);
    }
  };

  const startImportJob = async (config: any, selectedTables: string[]) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();

      if (!user) {
        toast.error('You must be logged in to start an import');
        return null;
      }

      // Create import job in database
      const { data: job, error } = await supabase
        .from('import_jobs')
        .insert({
          user_id: user.id,
          config,
          status: 'pending',
          total_tables: selectedTables.length,
        })
        .select()
        .single();

      if (error) {
        console.error('Failed to create import job:', error);
        toast.error('Failed to start import job');
        return null;
      }

      setActiveJob(job);
      setIsPolling(true);

      // Start the background processing via edge function
      const apiUrl = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/process-import-job`;
      const headers = {
        'Authorization': `Bearer ${import.meta.env.VITE_SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json',
      };

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          job_id: job.id,
          config,
          selected_tables: selectedTables,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start background import');
      }

      toast.success('Import started in background');
      return job.id;
    } catch (error) {
      console.error('Error starting import job:', error);
      toast.error('Failed to start import');
      return null;
    }
  };

  const cancelImportJob = async (jobId: string) => {
    try {
      const { error } = await supabase
        .from('import_jobs')
        .update({
          status: 'cancelled',
          updated_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        })
        .eq('id', jobId);

      if (error) {
        console.error('Failed to cancel import job:', error);
        return;
      }

      setActiveJob(null);
      setIsPolling(false);
      toast('Import cancelled');
    } catch (error) {
      console.error('Error cancelling import job:', error);
    }
  };

  const fetchJobStatus = async (jobId: string) => {
    try {
      const { data: job, error } = await supabase
        .from('import_jobs')
        .select('*')
        .eq('id', jobId)
        .single();

      if (error) {
        console.error('Failed to fetch job status:', error);
        return null;
      }

      return job as ImportJob;
    } catch (error) {
      console.error('Error fetching job status:', error);
      return null;
    }
  };

  // Poll for job updates
  useEffect(() => {
    if (isPolling && activeJob) {
      pollingIntervalRef.current = window.setInterval(async () => {
        const updatedJob = await fetchJobStatus(activeJob.id);

        if (updatedJob) {
          setActiveJob(updatedJob);

          // Stop polling if job is complete
          if (['completed', 'failed', 'cancelled'].includes(updatedJob.status)) {
            setIsPolling(false);

            if (updatedJob.status === 'completed') {
              toast.success(`✅ Import completed! ${updatedJob.imported_tables}/${updatedJob.total_tables} tables imported`, {
                duration: 5000,
              });
            } else if (updatedJob.status === 'failed') {
              toast.error(`❌ Import failed: ${updatedJob.error_message}`, {
                duration: 5000,
              });
            }
          }
        }
      }, 2000); // Poll every 2 seconds

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      };
    }
  }, [isPolling, activeJob]);

  // Check for active jobs on mount
  useEffect(() => {
    checkForActiveJobs();
  }, []);

  // Listen for auth changes - DON'T cancel job on logout, just stop polling
  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.onAuthStateChange(async (event, session) => {
        if (event === 'SIGNED_OUT' && activeJob) {
          // Stop polling but DON'T cancel the job - it continues in background
          setIsPolling(false);
          setActiveJob(null);
          toast('Import continues in background. Check status after logging back in.', {
            duration: 4000,
          });
        } else if (event === 'SIGNED_IN') {
          // Check for active jobs when user logs back in
          await checkForActiveJobs();
        }
      });

      authListenerRef.current = data;
    })();

    return () => {
      if (authListenerRef.current?.subscription) {
        authListenerRef.current.subscription.unsubscribe();
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [activeJob]);

  return {
    activeJob,
    startImportJob,
    cancelImportJob,
    isPolling,
  };
}
