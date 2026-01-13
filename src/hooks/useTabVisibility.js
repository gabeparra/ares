import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../services/api';

export function useTabVisibility() {
  return useQuery({
    queryKey: ['settings', 'tab-visibility'],
    queryFn: async () => {
      const response = await apiGet('/api/v1/settings/tab-visibility');
      const data = await response.json();
      return data.visibility || { sdapi: true };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

