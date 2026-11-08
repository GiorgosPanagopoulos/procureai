import { useState } from 'react';
import type { KeyboardEvent, Ref } from 'react';
import type { LoginText } from './loginText';

interface PasswordFieldProps {
  id: string;
  inputRef: Ref<HTMLInputElement>;
  text: LoginText;
}

export default function PasswordField({ id, inputRef, text }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  const readCapsLock = (e: KeyboardEvent<HTMLInputElement>) => setCapsLock(e.getModifierState('CapsLock'));

  return (
    <div>
      <label className="login-label" htmlFor={id}>{text.password}</label>
      <div className="login-password-wrap">
        <input
          id={id}
          ref={inputRef}
          name="password"
          type={visible ? 'text' : 'password'}
          autoComplete="current-password"
          className="login-input login-input--password"
          onKeyDown={readCapsLock}
          onKeyUp={readCapsLock}
          onBlur={() => setCapsLock(false)}
          aria-required="true"
          aria-describedby={capsLock ? `${id}-caps` : undefined}
        />
        <button
          type="button"
          className="login-eye"
          onClick={() => setVisible(v => !v)}
          aria-label={visible ? text.hidePassword : text.showPassword}
          aria-pressed={visible}
          aria-controls={id}
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
      <div aria-live="polite">
        {capsLock && (
          <span id={`${id}-caps`} className="login-caps">
            <CapsIcon />
            {text.capsLock}
          </span>
        )}
      </div>
    </div>
  );
}

const svgProps = {
  width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true,
};

const EyeIcon = () => (
  <svg {...svgProps}><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></svg>
);
const EyeOffIcon = () => (
  <svg {...svgProps}>
    <path d="M10.6 5.1A10.7 10.7 0 0112 5c6.4 0 10 7 10 7a17.6 17.6 0 01-3.2 4.1M6.6 6.6C3.8 8.4 2 12 2 12s3.6 7 10 7a9.7 9.7 0 005.4-1.6" />
    <path d="M9.9 9.9a3 3 0 004.2 4.2" /><line x1="2" y1="2" x2="22" y2="22" />
  </svg>
);
const CapsIcon = () => (
  <svg {...svgProps} width={16} height={16}><path d="M12 4l7 8h-4v4H9v-4H5z" /><line x1="9" y1="20" x2="15" y2="20" /></svg>
);
