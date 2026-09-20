import React, { useCallback, useState } from 'react';
import { uploadFile } from '../api';
import type { Dataset, Relationship } from '../api';

interface Props {
  sessionId: string | null;
  datasets: Dataset[];
  relationships: Relationship[];
  onUploaded: () => void;
  onDatasetRemoved: (id: string) => void;
  uploading: boolean;
  setUploading: (v: boolean) => void;
}

const fmtRows = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` :
  n >= 1_000 ? `${(n / 1_000).toFixed(0)}K` : `${n}`;

export const Sidebar: React.FC<Props> = ({
  sessionId, datasets, relationships,
  onUploaded, onDatasetRemoved,
  uploading, setUploading,
}) => {
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState(0);
  const [feedback, setFeedback] = useState<{ text: string; ok: boolean } | null>(null);

  const processFiles = useCallback(async (files: FileList | File[]) => {
    if (!sessionId) return;
    const valid = Array.from(files).filter(f =>
      f.name.endsWith('.csv') || f.name.endsWith('.xlsx')
    );
    if (!valid.length) {
      setFeedback({ text: 'Only CSV/XLSX supported', ok: false });
      return;
    }

    setUploading(true);
    setFeedback(null);

    for (const file of valid) {
      setFeedback({ text: `Uploading ${file.name}…`, ok: true });
      try {
        await uploadFile(sessionId, file, setProgress);
        setFeedback({ text: `✓ ${file.name}`, ok: true });
        onUploaded();
      } catch (e: unknown) {
        const msg = (e as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message ?? String(e);
        setFeedback({ text: `✗ ${msg}`, ok: false });
      }
    }

    setUploading(false);
    setTimeout(() => setFeedback(null), 3500);
  }, [sessionId, onUploaded, setUploading]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    processFiles(e.dataTransfer.files);
  };

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) processFiles(e.target.files);
    e.target.value = '';
  };

  return (
    <aside className="sidebar">
      {/* Upload */}
      <div className="sidebar-header">
        <div className="sidebar-label">Data sources</div>
        <label
          className={`upload-zone ${drag ? 'drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
        >
          <input
            type="file" accept=".csv,.xlsx" multiple hidden
            onChange={onInput}
            disabled={uploading || !sessionId}
          />
          <div className="upload-zone-icon">↑</div>
          <div className="upload-zone-text">
            <span className="upload-zone-cta">Upload files</span>
          </div>
          <div className="upload-zone-sub">CSV, XLSX · Max 25 MB</div>
        </label>

        {uploading && (
          <div className="upload-feedback" style={{ color: 'var(--text-3)' }}>
            <div>{feedback?.text}</div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}
        {!uploading && feedback && (
          <div className="upload-feedback" style={{ color: feedback.ok ? 'var(--emerald)' : 'var(--rose)' }}>
            {feedback.text}
          </div>
        )}
      </div>

      {/* Dataset list */}
      <div className="dataset-scroll">
        {datasets.length === 0 ? (
          <div className="dataset-empty">No files uploaded</div>
        ) : (
          datasets.map(ds => (
            <div key={ds.dataset_id} className="ds-card">
              <div className="ds-icon">
                {ds.source_file.endsWith('.xlsx') ? '⊞' : '≡'}
              </div>
              <div className="ds-info">
                <div className="ds-name" title={ds.display_name}>{ds.display_name}</div>
                <div className="ds-meta">{fmtRows(ds.row_count)} rows · {ds.column_count} cols</div>
              </div>
              <button
                className="ds-remove"
                onClick={() => onDatasetRemoved(ds.dataset_id)}
                title="Remove"
              >×</button>
            </div>
          ))
        )}
      </div>

      {/* Relationships */}
      {relationships.length > 0 && (
        <div className="rel-section">
          <div className="sidebar-label" style={{ marginBottom: 6 }}>Detected joins</div>
          {relationships.slice(0, 4).map(r => (
            <div key={r.relationship_id} className="rel-item">
              <div className={`rel-dot ${r.status === 'high_confidence' ? 'high' : 'low'}`} />
              <span style={{ flex: 1, wordBreak: 'break-all' }}>
                {r.left_column} ↔ {r.right_column}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-3)' }}>
                {Math.round(r.evidence_score * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
};
