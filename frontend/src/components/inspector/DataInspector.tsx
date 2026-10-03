import Icon from '../common/Icon';
import SupplierCard from './SupplierCard';
import BidCard from './BidCard';
import DataInspectorTabs from './DataInspectorTabs';
import { useInspectorData } from '../../hooks/useInspectorData';
import type { CatalogLoading } from '../../hooks/useCatalogData';
import type { Translations } from '../../i18n/translations';
import type { Bid, Message, RightTab, Supplier } from '../../types';

interface DataInspectorProps {
  messages: Message[];
  suppliers: Supplier[];
  bids: Bid[];
  loadingData: CatalogLoading;
  onLoadSuppliers: () => void;
  onLoadBids: () => void;
  rightTab: RightTab;
  onTabChange: (tab: RightTab) => void;
  onClearChat: () => void;
  t: Translations;
}

export default function DataInspector({
  messages, suppliers, bids, loadingData, onLoadSuppliers, onLoadBids,
  rightTab, onTabChange, onClearChat, t,
}: DataInspectorProps) {
  const {
    agentMessages, avgBidValue, activeBids, visibleSuppliers, visibleBids,
    showMoreSuppliers, toggleShowMoreSuppliers, showMoreBids, toggleShowMoreBids,
  } = useInspectorData(messages, suppliers, bids);

  return (
    <div className="right-panel">
      <DataInspectorTabs
        rightTab={rightTab}
        onTabChange={onTabChange}
        dataLabel={t.dataInspector}
        resultsLabel={t.results}
        resultsBadgeCount={agentMessages.length}
      />

      <div className="tab-content">
        {rightTab === 'data' ? (
          <>
            <p className="section-label">{t.databaseRecords}</p>

            <div className="data-cards-grid">
              {([
                { type: 'suppliers' as const, icon: 'suppliers', label: t.suppliers, count: suppliers.length, color: '#22d3ee', rgb: '34,211,238', load: onLoadSuppliers },
                { type: 'bids'      as const, icon: 'bids',      label: t.bids,      count: bids.length,      color: '#a78bfa', rgb: '167,139,250', load: onLoadBids },
              ]).map(({ type, icon, label, count, color, rgb, load }) => (
                <button
                  key={type}
                  className="count-card"
                  style={{
                    background: count > 0 ? `rgba(${rgb},0.08)` : 'var(--surface3)',
                    border: `1px solid ${count > 0 ? `rgba(${rgb},0.25)` : 'var(--border)'}`,
                  }}
                  onClick={load}
                >
                  {loadingData === type && (
                    <div className="card-loading-overlay">
                      <div className="card-spinner" style={{ borderColor: color, borderTopColor: 'transparent' }} />
                    </div>
                  )}
                  <div className="count-card-header">
                    <Icon name={icon} size={14} color={color} />
                    <span className="count-card-label" style={{ color: count > 0 ? color : 'var(--text2)' }}>{label}</span>
                  </div>
                  <div className="count-card-value" style={{ color: count > 0 ? 'var(--text)' : 'var(--text3)' }}>{count}</div>
                  <div className="count-card-sub">{count === 0 ? t.clickToLoad : t.recordsLoaded}</div>
                </button>
              ))}
            </div>

            {(suppliers.length > 0 || bids.length > 0) && (
              <div className="data-loaded-badge">
                <Icon name="check" size={12} color="var(--success)" />
                {t.dataSynced}
              </div>
            )}

            {bids.length > 0 && (
              <div className="quick-stats">
                <p className="section-label">{t.quickStats}</p>
                {[
                  { label: 'Avg bid value',  value: avgBidValue,          trend: '+8%', pos: true },
                  { label: 'Active bids',    value: String(activeBids),   trend: `+${activeBids}`, pos: true },
                  { label: 'Total bids',     value: String(bids.length),  trend: '' },
                ].map(s => (
                  <div key={s.label} className="stat-row">
                    <span className="stat-label">{s.label}</span>
                    <div className="stat-value-group">
                      <span className="stat-value">{s.value}</span>
                      {s.trend && (
                        <span className={`stat-trend ${s.pos ? 'positive' : 'warning'}`}>{s.trend}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {suppliers.length > 0 && (
              <div className="data-section">
                <p className="section-label">{t.suppliers} ({suppliers.length})</p>
                <div className="data-list">
                  {visibleSuppliers.map((s, i) => (
                    <SupplierCard key={i} supplier={s} />
                  ))}
                </div>
                {suppliers.length > 5 && (
                  <button className="show-more-btn" onClick={toggleShowMoreSuppliers}>
                    {showMoreSuppliers ? t.showLess : `${t.loadMore} (${suppliers.length - 5})`}
                  </button>
                )}
              </div>
            )}

            {bids.length > 0 && (
              <div className="data-section">
                <p className="section-label">{t.bids} ({bids.length})</p>
                <div className="data-list">
                  {visibleBids.map((b, i) => (
                    <BidCard key={i} bid={b} />
                  ))}
                </div>
                {bids.length > 5 && (
                  <button className="show-more-btn" onClick={toggleShowMoreBids}>
                    {showMoreBids ? t.showLess : `${t.loadMore} (${bids.length - 5})`}
                  </button>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            <p className="section-label">{t.agentResponses}</p>
            {agentMessages.length === 0 ? (
              <div className="results-empty">
                <Icon name="chart" size={32} color="var(--text3)" />
                <p className="results-empty-title">{t.noResults}</p>
                <p className="results-empty-desc">{t.noResultsDesc}</p>
              </div>
            ) : (
              <div className="results-list">
                {[...agentMessages].reverse().map((msg, i) => (
                  <div key={msg.id} className="result-card" style={{ animationDelay: `${i * 60}ms` }}>
                    <div className="result-card-header">
                      <span className="result-card-type">Query Result</span>
                      <span className="result-card-time">
                        {msg.timestamp.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="result-card-body">
                      {msg.text.length > 160 ? msg.text.slice(0, 157) + '…' : msg.text}
                    </div>
                    <div className="result-card-tags">
                      <span className="result-tag">Procurement</span>
                      {msg.toolUsed && <span className="result-tag">{msg.toolUsed}</span>}
                      {msg.usage && (
                        <span className="result-tag">${msg.usage.cost_usd.toFixed(4)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <div className="panel-footer">
        <div className="footer-stats">
          <span className="footer-dot">●</span> {suppliers.length} suppliers · {bids.length} bids
        </div>
        <button className="footer-clear-btn" onClick={onClearChat}>
          <Icon name="refresh" size={11} color="currentColor" /> {t.clearBtn}
        </button>
      </div>
    </div>
  );
}
