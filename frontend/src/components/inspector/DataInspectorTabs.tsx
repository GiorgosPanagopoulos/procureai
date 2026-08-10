import Icon from '../common/Icon';
import type { RightTab } from '../../types';

interface DataInspectorTabsProps {
  rightTab: RightTab;
  onTabChange: (tab: RightTab) => void;
  dataLabel: string;
  resultsLabel: string;
  resultsBadgeCount: number;
}

export default function DataInspectorTabs({
  rightTab, onTabChange, dataLabel, resultsLabel, resultsBadgeCount,
}: DataInspectorTabsProps) {
  return (
    <div className="tab-bar">
      {([
        { id: 'data',    label: dataLabel,    icon: 'suppliers' },
        { id: 'results', label: resultsLabel, icon: 'chart' },
      ] as const).map(tab => (
        <button
          key={tab.id}
          className={`tab-btn ${rightTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <Icon name={tab.icon} size={13} color={rightTab === tab.id ? 'var(--accent2)' : 'var(--text3)'} />
          {tab.label}
          {tab.id === 'results' && resultsBadgeCount > 0 && (
            <span className="tab-badge">{resultsBadgeCount}</span>
          )}
        </button>
      ))}
    </div>
  );
}
