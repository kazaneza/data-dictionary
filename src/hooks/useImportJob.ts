import { useEffect, useState, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { api } from '../lib/api';

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
  const isLoggedOutRef = useRef(false);
  const pollingStartTimeRef = useRef<number | null>(null);
  const MAX_POLLING_TIME = 24 * 60 * 60 * 1000; // 24 hours max polling time
  const STALE_JOB_THRESHOLD = 2 * 60 * 60 * 1000; // 2 hours - if job hasn't updated, consider it stuck

  const checkForActiveJobs = async () => {
    try {
      const authToken = localStorage.getItem('authToken');
      if (!authToken) return;

      const currentUser = localStorage.getItem('username') || 'unknown_user';

      const response = await api.get(`/api/import-jobs/user/${currentUser}?status=pending,in_progress`);
      const jobs = response.data;

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
      const authToken = localStorage.getItem('authToken');
      let currentUser = localStorage.getItem('username');

      if (!authToken) {
        toast.error('You must be logged in to start an import');
        return null;
      }

      if (!currentUser) {
        currentUser = 'unknown_user';
      }

      const response = await api.post('/api/import-jobs', {
        user_id: currentUser,
        config,
        total_tables: selectedTables.length,
      });

      const job = response.data;
      setActiveJob(job);
      setIsPolling(true);

      await api.post(`/api/import-jobs/${job.id}/process`, {
        config,
        selected_tables: selectedTables,
      });

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
      await api.put(`/api/import-jobs/${jobId}`, {
        status: 'cancelled',
        completed_at: new Date().toISOString(),
      });

      setActiveJob(null);
      setIsPolling(false);
      pollingStartTimeRef.current = null;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      toast('Import cancelled');
    } catch (error) {
      console.error('Error cancelling import job:', error);
    }
  };

  const fetchJobStatus = async (jobId: string) => {
    try {
      const response = await api.get(`/api/import-jobs/${jobId}`);
      return response.data as ImportJob;
    } catch (error) {
      console.error('Error fetching job status:', error);
      return null;
    }
  };

  useEffect(() => {
    if (isPolling && activeJob) {
      // Record when polling started
      if (!pollingStartTimeRef.current) {
        pollingStartTimeRef.current = Date.now();
      }

      pollingIntervalRef.current = window.setInterval(async () => {
        const updatedJob = await fetchJobStatus(activeJob.id);

        if (updatedJob) {
          setActiveJob(updatedJob);

          // Check if job is stuck (hasn't been updated in a while)
          if (updatedJob.updated_at) {
            const lastUpdate = new Date(updatedJob.updated_at).getTime();
            const timeSinceUpdate = Date.now() - lastUpdate;
            
            if (timeSinceUpdate > STALE_JOB_THRESHOLD && 
                ['pending', 'in_progress'].includes(updatedJob.status)) {
              console.warn('Job appears to be stuck - no updates for', Math.round(timeSinceUpdate / 60000), 'minutes');
              toast('Import appears to be stuck. Please check the worker process.', {
                duration: 5000,
                icon: '⚠️',
              });
            }
          }

          // Check if we've been polling too long
          if (pollingStartTimeRef.current) {
            const pollingDuration = Date.now() - pollingStartTimeRef.current;
            if (pollingDuration > MAX_POLLING_TIME) {
              console.warn('Polling timeout reached');
              setIsPolling(false);
              pollingStartTimeRef.current = null;
              toast('Import is taking longer than expected. Please check manually.', {
                duration: 5000,
                icon: '⏱️',
              });
              return;
            }
          }

          if (['completed', 'failed', 'cancelled'].includes(updatedJob.status)) {
            setIsPolling(false);
            pollingStartTimeRef.current = null;

            if (updatedJob.status === 'completed') {
              toast.success(`Import completed! ${updatedJob.imported_tables}/${updatedJob.total_tables} tables imported`, {
                duration: 5000,
              });
            } else if (updatedJob.status === 'failed') {
              toast.error(`Import failed: ${updatedJob.error_message}`, {
                duration: 5000,
              });
            }
          }
        } else {
          // If we can't fetch the job, it might have been deleted or there's a connection issue
          console.warn('Could not fetch job status - job may have been deleted or connection lost');
        }
      }, 2000);

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        pollingStartTimeRef.current = null;
      };
    } else {
      // Reset polling start time when not polling
      pollingStartTimeRef.current = null;
    }
  }, [isPolling, activeJob]);

  useEffect(() => {
    checkForActiveJobs();
  }, []);

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'authToken') {
        if (!e.newValue && activeJob) {
          setIsPolling(false);
          setActiveJob(null);
          isLoggedOutRef.current = true;
          toast('Import continues in background. Check status after logging back in.', {
            duration: 4000,
          });
        } else if (e.newValue && isLoggedOutRef.current) {
          isLoggedOutRef.current = false;
          checkForActiveJobs();
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
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
