import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { QueryResponse } from '../api';

const COLORS = ['#6366f1', '#8b5cf6', '#22d3ee', '#10b981', '#f59e0b', '#f43f5e', '#ec4899'];

const fmt = (v: unknown): string => {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
    if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
    if (!Number.isInteger(v)) return v.toFixed(2);
    return v.toLocaleString();
  }
  if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) {
    try { return new Date(v).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }); }
    catch { return v; }
  }
  return String(v);
};

const tt = {
  contentStyle: {
    background: '#161921',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 8,
    color: '#f4f4f5',
    fontSize: 12,
  },
  cursor: { fill: 'rgba(99,102,241,0.08)' },
};

interface Props { response: QueryResponse; }

export const ResponseCard: React.FC<Props> = ({ response }) => {
  const { result, explanation, validation, provenance, visualization, processing_stages: _stages } = response;

  // Derive chart type
  const vizType = (visualization?.type as string) ?? 'table';
  const compatible = (visualization?.compatible_types as string[]) ?? [vizType];
  const [chartType, setChartType] = useState<string>(vizType);

  /* ── Special states ── */
  if (response.plan_status === 'clarification') {
    return (
      <div className="r-clarify">
        🤔 {response.clarification_question}
      </div>
    );
  }

  if (response.plan_status === 'unsupported') {
    return (
      <div className="r-unsupported">
        🚫 {response.unsupported_reason}
      </div>
    );
  }

  if (validation?.status?.includes('BLOCKED')) {
    return (
      <div className="r-unsupported">
        ❌ {validation.blocking_reason ?? 'Query was blocked by validation.'}
      </div>
    );
  }

  /* ── Chart data ── */
  const cols = result?.columns ?? [];
  const rows = result?.rows ?? [];
  const xKey = (visualization?.x as string) || cols[0]?.name || '';
  const yKey = (visualization?.y as string) || cols[1]?.name || '';
  const chartData = rows.map((row) => {
    const obj: Record<string, unknown> = {};
    cols.forEach((c, i) => { obj[c.name] = row[i]; });
    return obj;
  });

  /* ── Determine badge ── */
  const vScore = validation?.validation_score ?? 1;
  const badgeClass = validation?.status?.includes('BLOCKED') ? 'err' : vScore < 0.5 ? 'warn' : 'ok';
  const badgeLabel = badgeClass === 'err' ? '✗ Blocked' : badgeClass === 'warn' ? '⚠ Low confidence' : '✓ Verified';

  /* ── Render viz ── */
  const renderViz = () => {
    const type = chartType || vizType;

    if (type === 'kpi' && rows.length === 1) {
      return (
        <div className="r-kpi">
          <div className="kpi-val">{fmt(rows[0]?.[0])}</div>
          <div className="kpi-lbl">{cols[0]?.name?.replace(/_/g, ' ')}</div>
        </div>
      );
    }

    if ((type === 'line' || type === 'trend') && chartData.length > 1) {
      return (
        <div className="r-chart">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 8, right: 20, bottom: 8, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: '#52525b' }} tickFormatter={v => String(v).slice(0, 10)} />
              <YAxis tick={{ fontSize: 10, fill: '#52525b' }} tickFormatter={v => fmt(v)} width={60} />
              <Tooltip {...tt} formatter={v => [fmt(v), yKey]} labelFormatter={l => fmt(l)} />
              <Line type="monotone" dataKey={yKey} stroke="#6366f1" strokeWidth={2} dot={{ r: 2.5, fill: '#6366f1' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    if (type === 'bar' && chartData.length > 0) {
      return (
        <div className="r-chart">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 8, right: 20, bottom: chartData.length > 5 ? 30 : 8, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: '#52525b' }} angle={chartData.length > 5 ? -30 : 0} textAnchor={chartData.length > 5 ? 'end' : 'middle'} tickFormatter={v => String(v).slice(0, 12)} />
              <YAxis tick={{ fontSize: 10, fill: '#52525b' }} tickFormatter={v => fmt(v)} width={60} />
              <Tooltip {...tt} formatter={v => [fmt(v), yKey]} cursor={tt.cursor} />
              <Bar dataKey={yKey} radius={[3, 3, 0, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    if (type === 'pie' && chartData.length > 0 && chartData.length <= 8) {
      return (
        <div className="r-chart">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={chartData} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={90} paddingAngle={2}
                label={({ name, percent }) => `${String(name).slice(0, 10)} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#52525b', strokeWidth: 0.5 }}>
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...tt} formatter={v => [fmt(v)]} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );
    }

    /* Default: table */
    if (rows.length === 0) {
      return <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-3)', fontSize: 12 }}>No data returned.</div>;
    }

    return (
      <div className="r-table-wrap">
        <table className="r-table">
          <thead>
            <tr>{cols.map(c => <th key={c.name}>{c.name.replace(/_/g, ' ')}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {row.map((val, j) => (
                  <td key={j} className={typeof val === 'number' ? 'num' : ''}>
                    {fmt(val)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const warnings = [
    ...(validation?.warnings ?? []),
    ...(result?.data_quality?.warnings ?? []),
    ...(explanation?.warnings ?? []),
  ].filter(Boolean);

  return (
    <div className="r-card">
      {/* Header */}
      <div className="r-header">
        <span className="r-header-label">Analysis</span>
        {result && (
          <span className="r-exec-time">{result.execution_time_ms}ms · {result.row_count} rows</span>
        )}
        <span className={`r-badge ${badgeClass}`}>{badgeLabel}</span>
      </div>

      {/* Answer */}
      {explanation?.answer && (
        <div className="r-answer">{explanation.answer}</div>
      )}

      {/* Key points */}
      {(explanation?.key_points?.length ?? 0) > 0 && (
        <div className="r-points">
          {explanation!.key_points.map((p, i) => (
            <div key={i} className="r-point">{p}</div>
          ))}
        </div>
      )}

      {/* Chart tabs */}
      {compatible.length > 1 && (
        <div className="r-tabs">
          {compatible.map(t => (
            <button
              key={t}
              className={`r-tab ${chartType === t ? 'active' : ''}`}
              onClick={() => setChartType(t)}
            >
              {t === 'bar' ? '▪ Bar' : t === 'line' ? '∿ Line' : t === 'pie' ? '◎ Pie' : t === 'kpi' ? '# KPI' : '⊞ Table'}
            </button>
          ))}
        </div>
      )}

      {/* Visualization */}
      {result && renderViz()}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="r-warn">
          <span>⚠</span>
          <div>{warnings.map((w, i) => <div key={i}>{w}</div>)}</div>
        </div>
      )}

      {/* Footer: provenance */}
      {provenance && (
        <div className="r-footer">
          <span>📁 {provenance.datasets_used.join(', ')}</span>
          {provenance.operations_summary.length > 0 && (
            <span>·&nbsp;{provenance.operations_summary.slice(0, 2).join(' › ')}</span>
          )}
          {provenance.compiled_sql && (
            <span
              className="r-footer-sql"
              title={provenance.compiled_sql}
            >
              {provenance.compiled_sql.replace(/\n/g, ' ').slice(0, 80)}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
