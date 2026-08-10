import type { Supplier } from '../../types';

function StarRating({ rating }: { rating: number }) {
  return (
    <span>
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} className={i < Math.round(rating) ? 'star-filled' : 'star-empty'}>★</span>
      ))}
    </span>
  );
}

interface SupplierCardProps {
  supplier: Supplier;
}

export default function SupplierCard({ supplier }: SupplierCardProps) {
  return (
    <div className="data-item">
      <div className="data-item-row">
        <span className="data-item-name">{supplier.name}</span>
        <span className="category-badge">{supplier.category}</span>
      </div>
      <div className="data-item-row">
        <StarRating rating={supplier.rating} />
        <span className="data-item-sub">{supplier.contact}</span>
      </div>
    </div>
  );
}
