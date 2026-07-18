import { useState, useCallback } from 'react';

const API_BASE = '/api';

/**
 * Hook for making REST API calls with loading/error states.
 */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerPipeline = useCallback(async (source = 'USGS') => {
    return fetchData('/trigger', {
      method: 'POST',
      body: JSON.stringify({ source }),
    });
  }, [fetchData]);

  return { fetchData, triggerPipeline, loading, error };
}
