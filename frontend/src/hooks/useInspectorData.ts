import { useState } from 'react';
import type { Bid, Message, Supplier } from '../types';

export interface UseInspectorDataResult {
  agentMessages: Message[];
  avgBidValue: string;
  activeBids: number;
  visibleSuppliers: Supplier[];
  visibleBids: Bid[];
  showMoreSuppliers: boolean;
  toggleShowMoreSuppliers: () => void;
  showMoreBids: boolean;
  toggleShowMoreBids: () => void;
}

export function useInspectorData(messages: Message[], suppliers: Supplier[], bids: Bid[]): UseInspectorDataResult {
  const [showMoreSuppliers, setShowMoreSuppliers] = useState(false);
  const [showMoreBids, setShowMoreBids] = useState(false);

  const agentMessages = messages.filter(m => m.sender === 'agent');

  const avgBidValue = bids.length > 0
    ? (bids.reduce((s, b) => s + b.total_price, 0) / bids.length)
        .toLocaleString('el-GR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
    : '—';
  const activeBids = bids.filter(b => b.status.toLowerCase() === 'pending').length;

  const visibleSuppliers = showMoreSuppliers ? suppliers : suppliers.slice(0, 5);
  const visibleBids      = showMoreBids      ? bids      : bids.slice(0, 5);

  return {
    agentMessages, avgBidValue, activeBids, visibleSuppliers, visibleBids,
    showMoreSuppliers, toggleShowMoreSuppliers: () => setShowMoreSuppliers(p => !p),
    showMoreBids, toggleShowMoreBids: () => setShowMoreBids(p => !p),
  };
}
