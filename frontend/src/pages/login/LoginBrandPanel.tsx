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

// Static grid and rings, decorative only.
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
        <g className="login-desktop-only" stroke="currentColor" strokeOpacity="0.12">
          <line x1="74%" y1="0" x2="74%" y2="100%" />
          <line x1="0" y1="63%" x2="100%" y2="63%" />
        </g>
      </svg>
      <svg className="login-brand__rings login-desktop-only" viewBox="0 0 820 820" focusable="false">
        <g fill="none" stroke="currentColor" strokeOpacity="0.12">
          <circle cx="410" cy="410" r="130" />
          <circle cx="410" cy="410" r="205" />
          <circle cx="410" cy="410" r="285" />
          <circle cx="410" cy="410" r="390" />
        </g>
        <g fill="currentColor" fillOpacity="0.5">
          <circle cx="356" cy="215" r="2.5" />
          <circle cx="507" cy="313" r="3.5" />
          <circle cx="258" cy="519" r="3" />
        </g>
      </svg>
    </div>
  );
}
