interface ErrorFallbackProps {
  error: Error;
}

export default function ErrorFallback({ error }: ErrorFallbackProps) {
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1rem',
      background: 'var(--bg)',
      color: 'var(--text)',
    }}>
      <h2 style={{ margin: 0, color: 'var(--text)' }}>Something went wrong</h2>
      <p style={{ margin: 0, color: 'var(--text2)', fontSize: '0.875rem' }}>{error.message}</p>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '0.5rem 1.25rem',
          borderRadius: '6px',
          border: 'none',
          background: 'var(--accent2)',
          color: '#fff',
          cursor: 'pointer',
          fontSize: '0.875rem',
        }}
      >
        Reload
      </button>
    </div>
  );
}
