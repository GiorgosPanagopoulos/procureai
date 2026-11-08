import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';

export type BackendStatus = 'checking' | 'waking' | 'ready' | 'degraded' | 'offline';

// Container Apps scales to zero, so the first request can take ~20s.
// The probe also warms the backend while the user types.
const READY_TIMEOUT_MS = 45000;
const WAKING_AFTER_MS = 2500;

export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    let active = true;
    const wakingTimer = setTimeout(() => {
      if (active) setStatus(s => (s === 'checking' ? 'waking' : s));
    }, WAKING_AFTER_MS);

    apiFetch('/health/ready', { timeoutMs: READY_TIMEOUT_MS, skipAuthRedirect: true })
      .then(res => { if (active) setStatus(res.ok ? 'ready' : 'degraded'); })
      .catch(() => { if (active) setStatus('offline'); })
      .finally(() => clearTimeout(wakingTimer));

    return () => {
      active = false;
      clearTimeout(wakingTimer);
    };
  }, []);

  return status;
}
