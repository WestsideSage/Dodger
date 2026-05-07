import { useEffect, useState } from 'react';

export function useApiResource<T>(url: string, onLoad?: (data: T) => void) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`Failed to fetch ${url}`);
        return res.json();
      })
      .then((payload: T) => {
        if (!cancelled) {
          setData(payload);
          if (onLoad) onLoad(payload);
        }
      })
      .catch(err => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [url, onLoad]);

  return { data, loading, error, setData, setError, setLoading };
}
