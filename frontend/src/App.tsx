import { useEffect, useState, useCallback } from 'react';
import './index.css';
import { createSession, getSession, removeDataset, getApiBaseUrl, setApiBaseUrl } from './api';
import type { Dataset, Relationship } from './api';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [customBackendUrl, setCustomBackendUrl] = useState(getApiBaseUrl());

  const refresh = useCallback(async (id: string) => {
    try {
      const info = await getSession(id);
      setDatasets(info.datasets);
      setRelationships(info.relationships);
    } catch {
      // Session expired — create a new one
      try {
        const newId = await createSession();
        setSessionId(newId);
        sessionStorage.setItem('sid', newId);
        setDatasets([]);
        setRelationships([]);
      } catch {
        setError(`Cannot connect to backend at ${getApiBaseUrl()}`);
      }
    }
  }, []);

  const initSession = useCallback(() => {
    setError('');
    const stored = sessionStorage.getItem('sid');
    if (stored) {
      setSessionId(stored);
      refresh(stored);
    } else {
      createSession()
        .then(id => {
          setSessionId(id);
          sessionStorage.setItem('sid', id);
        })
        .catch(() => setError(`Cannot connect to backend at ${getApiBaseUrl()}`));
    }
  }, [refresh]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  const onUploaded = useCallback(() => {
    if (sessionId) refresh(sessionId);
  }, [sessionId, refresh]);

  const onRemove = useCallback(async (dsId: string) => {
    if (!sessionId) return;
    try { await removeDataset(sessionId, dsId); } catch { /* ignore */ }
    refresh(sessionId);
  }, [sessionId, refresh]);

  const totalRows = datasets.reduce((s, d) => s + d.row_count, 0);

  const handleSaveBackendUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (customBackendUrl.trim()) {
      setApiBaseUrl(customBackendUrl.trim());
      setError('');
      sessionStorage.removeItem('sid');
      window.location.reload();
    }
  };

  if (error) {
    return (
      <div className="app-shell" style={{ gridTemplateColumns: '1fr', gridTemplateRows: '48px 1fr' }}>
        <header className="topbar">
          <div className="topbar-logo">
            <div className="logo-icon">✦</div>
            AI Analyst
          </div>
        </header>
        <div className="disconnect-view" style={{ maxWidth: 540, margin: '40px auto', padding: '32px 24px' }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>⚡</div>
          <h3 style={{ fontSize: 20, marginBottom: 8 }}>Backend unreachable</h3>
          <p style={{ color: 'var(--text-secondary, #94a3b8)', fontSize: 14, marginBottom: 20 }}>{error}</p>
          
          <form onSubmit={handleSaveBackendUrl} style={{ width: '100%', marginBottom: 20 }}>
            <label style={{ display: 'block', textAlign: 'left', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>
              Backend API URL (Render or Local):
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={customBackendUrl}
                onChange={(e) => setCustomBackendUrl(e.target.value)}
                placeholder="https://data-qa-backend.onrender.com/api/v1"
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(0,0,0,0.25)',
                  color: '#fff',
                  fontSize: 14,
                }}
              />
              <button
                type="submit"
                className="retry-btn"
                style={{ whiteSpace: 'nowrap', padding: '10px 18px', cursor: 'pointer' }}
              >
                Connect
              </button>
            </div>
          </form>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              type="button"
              className="retry-btn"
              onClick={() => { setError(''); initSession(); }}
              style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', cursor: 'pointer' }}
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="app-shell">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="logo-icon">✦</div>
          AI Analyst
        </div>
        <div className="topbar-badge">Beta</div>
        <div className="topbar-spacer" />
        {datasets.length > 0 && (
          <div className="topbar-meta">
            {datasets.length} file{datasets.length !== 1 ? 's' : ''} · {totalRows.toLocaleString()} rows
          </div>
        )}
        <div className="status-pill">
          <div className="dot" />
          {sessionId ? 'Connected' : 'Connecting…'}
        </div>
      </header>

      {/* Sidebar */}
      <Sidebar
        sessionId={sessionId}
        datasets={datasets}
        relationships={relationships}
        onUploaded={onUploaded}
        onDatasetRemoved={onRemove}
        uploading={uploading}
        setUploading={setUploading}
      />

      {/* Chat */}
      <ChatArea sessionId={sessionId} hasDatasets={datasets.length > 0} />
    </div>
  );
}

export default App;
