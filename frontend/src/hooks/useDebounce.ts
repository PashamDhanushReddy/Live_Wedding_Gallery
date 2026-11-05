import { useState, useEffect } from 'react';

/**
 * Custom hook to debounce a fast-changing value (e.g. search query).
 * @param value The value to debounce.
 * @param delay The delay in milliseconds (default: 350ms).
 */
export function useDebounce<T>(value: T, delay = 350): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

