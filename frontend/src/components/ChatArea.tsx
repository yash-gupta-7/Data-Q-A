import React, { useEffect, useRef, useState } from 'react';
import type { QueryResponse } from '../api';
import { submitQuery } from '../api';
import { ResponseCard } from './ResponseCard';
import { ErrorBoundary } from './ErrorBoundary';

type Message =
  | { role: 'user'; content: string }
  | { role: 'assistant'; error?: string; response?: QueryResponse };

interface Props {
  sessionId: string | null;
  hasDatasets: boolean;
}

const SUGGESTIONS = [
  'What is the total revenue?',
  'Show revenue by country',
  'Monthly revenue trend',
  'Which region has the highest sales?',
  'Compare India vs UAE revenue',
];

export const ChatArea: React.FC<Props> = ({ sessionId, hasDatasets }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const send = async (q: string = question) => {
    const text = q.trim();
    if (!text || !sessionId || loading) return;

    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setQuestion('');
    setLoading(true);

    try {
      const resp = await submitQuery(sessionId, text);
      setMessages(prev => [...prev, { role: 'assistant', response: resp }]);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message ?? 'Something went wrong. Please try again.';
      setMessages(prev => [...prev, { role: 'assistant', error: msg }]);
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const onInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 130)}px`;
  };

  return (
    <div className="chat-area">
      <div className="message-feed" ref={feedRef}>

        {/* ── Empty state ── */}
        {messages.length === 0 && !loading && (
          <div className="empty-state">
            <div className="empty-icon">✦</div>
            <h2>Ask anything about your data</h2>
            <p>
              Upload a CSV or XLSX file, then ask questions in plain English.
              Every answer is computed by DuckDB and verified before display.
            </p>
            {hasDatasets && (
              <div className="chips">
                {SUGGESTIONS.map(s => (
                  <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}
            {!hasDatasets && (
              <div className="no-data-note">Upload a file to get started</div>
            )}
          </div>
        )}

        {/* ── Messages ── */}
        {messages.map((msg, i) => {
          if (msg.role === 'user') {
            return (
              <div key={i} className="msg-row user">
                <div className="user-bubble">{msg.content}</div>
              </div>
            );
          }

          // Assistant
          if (msg.error) {
            return (
              <div key={i} className="msg-row assistant">
                <div className="error-bubble">⚠ {msg.error}</div>
              </div>
            );
          }

          if (msg.response) {
            return (
              <div key={i} className="msg-row assistant">
                <ErrorBoundary>
                  <ResponseCard response={msg.response} />
                </ErrorBoundary>
              </div>
            );
          }

          return null;
        })}

        {/* ── Typing indicator ── */}
        {loading && (
          <div className="msg-row typing-row assistant">
            <div className="typing-bubble">
              <div className="typing-dots">
                <div className="t-dot" />
                <div className="t-dot" />
                <div className="t-dot" />
              </div>
              <span className="typing-label">Analyzing…</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Input bar ── */}
      <div className="input-bar">
        <div className="input-wrap">
          <textarea
            className="q-input"
            placeholder={
              !sessionId ? 'Starting session…'
              : !hasDatasets ? 'Upload a file first…'
              : 'Ask a question… (Enter to send)'
            }
            value={question}
            onChange={onInput}
            onKeyDown={onKey}
            disabled={loading || !sessionId || !hasDatasets}
            rows={1}
          />
          <button
            className="send-btn"
            onClick={() => send()}
            disabled={loading || !question.trim() || !sessionId || !hasDatasets}
            title="Send"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
};
