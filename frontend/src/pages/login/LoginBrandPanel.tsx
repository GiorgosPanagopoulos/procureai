import { useId } from 'react';
import Icon from '../../components/common/Icon';
import { BRAND_CHIPS, type LoginText } from './loginText';

// Below 900px this collapses to a compact header: logo, name, chips.
export default function LoginBrandPanel({ text }: { text: LoginText }) {
  return (
    <section className="login-brand" aria-label="ProcureAI">
      <Backdrop />

      <div className="login-brand__logo-row">
        <div className="login-brand__logo"><Icon name="logo" size={22} color="#5e95ff" /></div>
        <div>
          <p className="login-brand__name">ProcureAI</p>
          <p className="login-brand__tagline">{text.tagline}</p>
        </div>
      </div>

      <div className="login-brand__body">
        <p className="login-brand__headline">
          {text.headlineLead} <span className="login-gold">{text.headlineAccent}</span>.
        </p>
        <p className="login-brand__desc">{text.description}</p>
        <ul className="login-brand__chips" aria-label={text.chipsLabel}>
          {BRAND_CHIPS.map(chip => <li key={chip}>{chip}</li>)}
        </ul>
      </div>

      <p className="login-brand__footer">FastAPI · LangChain · Claude · Atlas Vector Search</p>
    </section>
  );
}

// Nodes: documents (squares), suppliers (circles), bids (small dots).
// Static and decorative only.
const NODES: Array<[number, number, 'doc' | 'supplier' | 'bid']> = [
  [120, 140, 'doc'], [300, 90, 'supplier'], [470, 170, 'bid'], [610, 70, 'doc'],
  [220, 300, 'bid'], [400, 330, 'supplier'], [580, 280, 'doc'], [700, 380, 'bid'],
  [140, 470, 'supplier'], [330, 520, 'doc'], [520, 470, 'bid'], [660, 560, 'supplier'],
  [250, 660, 'bid'], [450, 650, 'supplier'], [620, 720, 'doc'],
];
const EDGES: Array<[number, number]> = [
  [0, 1], [1, 2], [2, 3], [0, 4], [1, 5], [4, 5], [5, 6], [6, 3], [6, 7],
  [4, 8], [5, 9], [8, 9], [9, 10], [6, 10], [10, 11], [7, 11],
  [9, 12], [12, 13], [10, 13], [13, 14], [11, 14],
];

function Backdrop() {
  const gridId = `login-grid-${useId().replace(/:/g, '')}`;
  return (
    <div className="login-brand__backdrop" aria-hidden="true">
      <svg className="login-brand__grid" focusable="false">
        <defs>
          <pattern id={gridId} width="120" height="120" patternUnits="userSpaceOnUse">
            <path d="M120 0H0V120" fill="none" stroke="currentColor" strokeOpacity="0.07" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#${gridId})`} />
      </svg>
      <svg className="login-brand__graph login-desktop-only" viewBox="0 0 820 800" focusable="false">
        <g stroke="currentColor" strokeOpacity="0.14" strokeWidth="1">
          {EDGES.map(([a, b]) => (
            <line key={`${a}-${b}`} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />
          ))}
        </g>
        {NODES.map(([x, y, kind], i) =>
          kind === 'doc' ? (
            <rect key={i} x={x - 7} y={y - 9} width="14" height="18" rx="2"
              fill="#0b1022" stroke="currentColor" strokeOpacity="0.4" />
          ) : kind === 'supplier' ? (
            <circle key={i} cx={x} cy={y} r="8" fill="#0b1022" stroke="currentColor" strokeOpacity="0.45" />
          ) : (
            <circle key={i} cx={x} cy={y} r="3" fill="currentColor" fillOpacity="0.5" />
          ),
        )}
      </svg>
    </div>
  );
}
