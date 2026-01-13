import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../services/api';

const AGENT_POLLING_KEY = 'ares_agent_auto_polling';

// Get auto-polling preference from localStorage
const getAutoPolling = () => {
  const stored = localStorage.getItem(AGENT_POLLING_KEY);
  return stored === null ? true : stored === 'true';
};

// Set auto-polling preference in localStorage
const setAutoPolling = (value) => {
  localStorage.setItem(AGENT_POLLING_KEY, String(value));
};

export function useAgentStatus(autoPolling = null) {
  const enabled = autoPolling !== null ? autoPolling : getAutoPolling();
  
  return useQuery({
    queryKey: ['agent', 'status'],
    queryFn: async () => {
      const res = await apiGet("/api/v1/agent/status");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(errorData.error || `Status check failed: ${res.status}`);
      }
      return res.json();
    },
    refetchInterval: enabled ? 5000 : false,
    staleTime: 3000, // Consider data stale after 3 seconds
  });
}

export function useAgentAction() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ action, parameters, force = true }) => {
      const res = await apiPost("/api/v1/agent/action", {
        action,
        parameters,
        force,
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.error || `Request failed with status ${res.status}`);
      }
      
      return res.json();
    },
    onSuccess: () => {
      // Invalidate and refetch agent status after action
      queryClient.invalidateQueries({ queryKey: ['agent', 'status'] });
    },
  });
}

export function useAgentLogs() {
  const queryClient = useQueryClient();
  
  return useQuery({
    queryKey: ['agent', 'logs'],
    queryFn: async () => {
      const res = await apiGet("/api/v1/agent/logs");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        // Return error in data structure so UI can display it
        return { error: errorData.error || `Failed to fetch logs: ${res.status}` };
      }
      const data = await res.json();
      return data;
    },
    enabled: false, // Only fetch when explicitly requested
    retry: false, // Don't retry on failure
    staleTime: 0, // Always consider data stale so refetch works
  });
}

export { getAutoPolling, setAutoPolling };

