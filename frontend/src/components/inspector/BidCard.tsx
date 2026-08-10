import type { Bid } from '../../types';

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const cls = s === 'accepted' ? 'status-pill status-pill-accepted'
            : s === 'rejected' ? 'status-pill status-pill-rejected'
            :                    'status-pill status-pill-pending';
  return <span className={cls}>{status}</span>;
}

interface BidCardProps {
  bid: Bid;
}

export default function BidCard({ bid }: BidCardProps) {
  return (
    <div className="data-item">
      <div className="data-item-row">
        <span className="data-item-sub">
          Supplier: <span style={{ color: 'var(--text)' }}>{bid.supplier_id}</span>
        </span>
        <StatusPill status={bid.status} />
      </div>
      <div className="data-item-row">
        <span className="data-item-price">
          {bid.total_price.toLocaleString('el-GR', { style: 'currency', currency: 'EUR' })}
        </span>
        <span className="data-item-sub">{bid.delivery_days}d delivery</span>
      </div>
    </div>
  );
}
