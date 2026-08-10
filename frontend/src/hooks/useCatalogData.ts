import { useState } from 'react';
import * as Sentry from '@sentry/react';
import { toast } from 'sonner';
import { fetchBids, fetchSuppliers } from '../api/chat';
import type { Bid, Supplier } from '../types';

export type CatalogLoading = 'suppliers' | 'bids' | null;

export interface UseCatalogDataResult {
  suppliers: Supplier[];
  bids: Bid[];
  loadingData: CatalogLoading;
  loadSuppliers: () => Promise<void>;
  loadBids: () => Promise<void>;
}

export function useCatalogData(): UseCatalogDataResult {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [bids, setBids] = useState<Bid[]>([]);
  const [loadingData, setLoadingData] = useState<CatalogLoading>(null);

  const loadSuppliers = async () => {
    setLoadingData('suppliers');
    try {
      const data = await fetchSuppliers();
      setSuppliers(data);
      toast.success(`Loaded ${data.length} suppliers`);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' } });
      toast.error(err instanceof Error ? err.message : 'Failed to load suppliers');
    } finally {
      setLoadingData(null);
    }
  };

  const loadBids = async () => {
    setLoadingData('bids');
    try {
      const data = await fetchBids();
      setBids(data);
      toast.success(`Loaded ${data.length} bids`);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' } });
      toast.error(err instanceof Error ? err.message : 'Failed to load bids');
    } finally {
      setLoadingData(null);
    }
  };

  return { suppliers, bids, loadingData, loadSuppliers, loadBids };
}
