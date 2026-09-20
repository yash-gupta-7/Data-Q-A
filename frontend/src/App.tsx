import { useEffect, useState, useCallback } from 'react';
import './index.css';
import { createSession, getSession, removeDataset } from './api';
import type { Dataset, Relationship } from './api';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

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
        setError('Cannot connect to backend.');
      }
    }
  }, []);

  useEffect(() => {
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
        .catch(() => setError('Cannot connect to backend at http://localhost:8000'));
    }
  }, [refresh]);

  const onUploaded = useCallback(() => {
    if (sessionId) refresh(sessionId);
  }, [sessionId, refresh]);

  const onRemove = useCallback(async (dsId: string) => {
    if (!sessionId) return;
    try { await removeDataset(sessionId, dsId); } catch { /* ignore */ }
    refresh(sessionId);
  }, [sessionId, refresh]);

  const totalRows = datasets.reduce((s, d) => s + d.row_count, 0);

  if (error) {
    return (
      <div className="app-shell" style={{ gridTemplateColumns: '1fr', gridTemplateRows: '48px 1fr' }}>
        <header className="topbar">
          <div className="topbar-logo">
            <div className="logo-icon">✦</div>
            AI Analyst
          </div>
        </header>
        <div className="disconnect-view">
          <div style={{ fontSize: 32 }}>⚡</div>
          <h3>Backend unreachable</h3>
          <p>{error}</p>
          <p style={{ fontSize: 12 }}>Make sure uvicorn is running on port 8000.</p>
          <button className="retry-btn" onClick={() => { setError(''); window.location.reload(); }}>
            Retry
          </button>
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
