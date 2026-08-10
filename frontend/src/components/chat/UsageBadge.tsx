import type { UsageInfo } from '../../types';

interface UsageBadgeProps {
  usage: UsageInfo;
}

export default function UsageBadge({ usage }: UsageBadgeProps) {
  const tooltip = [
    `Input: ${usage.input_tokens} tokens`,
    `Output: ${usage.output_tokens} tokens`,
    usage.cache_creation_tokens ? `Cache write: ${usage.cache_creation_tokens}` : '',
    usage.cache_read_tokens     ? `Cache read: ${usage.cache_read_tokens}` : '',
  ].filter(Boolean).join(' · ');

  return (
    <div className="usage-badge" title={tooltip}>
      ↑{usage.input_tokens} ↓{usage.output_tokens} · ${usage.cost_usd.toFixed(4)}
    </div>
  );
}
