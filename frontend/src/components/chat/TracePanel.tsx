import { useState } from 'react';
import { STEP_META } from '../../i18n/translations';
import type { Language, TraceStep } from '../../types';

interface TracePanelProps {
  trace: TraceStep[];
  lang: Language;
  viewLabel: string;
  hideLabel: string;
}

export default function TracePanel({ trace, lang, viewLabel, hideLabel }: TracePanelProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="trace-panel">
      <button className="trace-toggle" onClick={() => setOpen(p => !p)}>
        <span className="trace-toggle-icon">{open ? '▲' : '▼'}</span>
        {open ? hideLabel : viewLabel}
      </button>
      {open && (
        <div className="trace-steps">
          {trace.map((step, i) => {
            const meta = STEP_META[step.type];
            const label = lang === 'gr' ? meta.label_gr : meta.label_en;
            const body = step.type === 'tool_call'
              ? `${step.tool}(${step.input ?? ''})`
              : (step.content ?? '');
            return (
              <div key={i} className={`trace-step trace-step-${step.type}`}>
                <span className="trace-step-icon">{meta.icon}</span>
                <div className="trace-step-body">
                  <span className="trace-step-label">{label}</span>
                  <p className="trace-step-text">{body}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
