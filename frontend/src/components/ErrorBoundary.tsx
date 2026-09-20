import React from 'react';

interface Props { children: React.ReactNode; }
interface State { hasError: boolean; error: string; }

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: '' };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, error: err.message };
  }

  componentDidCatch(err: Error, info: React.ErrorInfo) {
    console.error('[ResponseCard error]', err, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="r-card">
          <div className="r-error">
            <div style={{ fontSize: 18, marginBottom: 6 }}>⚠️</div>
            <div>Failed to render response.</div>
            <div style={{ marginTop: 4, color: 'var(--text-3)', fontSize: 11 }}>
              {this.state.error}
            </div>
            <button
              style={{ marginTop: 10, padding: '4px 12px', background: 'var(--card-hover)', border: '1px solid var(--border-hi)', borderRadius: 6, color: 'var(--text-2)', cursor: 'pointer', fontSize: 12 }}
              onClick={() => this.setState({ hasError: false, error: '' })}
            >
              Dismiss
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
