import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: BASE });

export type Dataset = {
  dataset_id: string;
  display_name: string;
  source_file: string;
  sheet_name?: string;
  row_count: number;
  column_count: number;
  status: string;
  warnings: string[];
  columns: Column[];
};

export type Column = {
  name: string;
  physical_type: string;
  semantic_type: string;
  nullable: boolean;
  unique_ratio: number;
  sample_values: unknown[];
  quality: { null_count: number; null_pct: number; pii_detected: string[] };
};

export type Relationship = {
  relationship_id: string;
  left_dataset: string;
  left_column: string;
  right_dataset: string;
  right_column: string;
  relationship_type: string;
  status: string;
  evidence_score: number;
  overlap_ratio: number;
};

export type SessionInfo = {
  session_id: string;
  created_at: string;
  datasets: Dataset[];
  relationships: Relationship[];
  readiness: {
    files_processed: number;
    datasets_detected: number;
    total_rows: number;
    total_columns: number;
    relationships: unknown[];
    warnings: string[];
    skipped_sheets: string[];
  };
  message_count: number;
};

export type QueryResponse = {
  question: string;
  plan_status: string;
  clarification_question?: string;
  unsupported_reason?: string;
  result?: {
    columns: { name: string; type: string }[];
    rows: unknown[][];
    row_count: number;
    truncated: boolean;
    execution_time_ms: number;
    data_quality: {
      rows_analyzed: number;
      nulls_excluded: Record<string, number>;
      warnings: string[];
    };
  };
  validation?: {
    status: string;
    validation_score: number;
    warnings: string[];
    blocking_reason?: string;
  };
  explanation?: {
    answer: string;
    key_points: string[];
    assumptions: string[];
    warnings: string[];
  };
  provenance?: {
    datasets_used: string[];
    columns_used: string[];
    rows_analyzed: number;
    operations_summary: string[];
    compiled_sql: string;
  };
  visualization?: Record<string, unknown>;
  processing_stages: string[];
};

export const createSession = async (): Promise<string> => {
  const res = await api.post('/sessions');
  return res.data.data.session_id as string;
};

export const getSession = async (id: string): Promise<SessionInfo> => {
  const res = await api.get(`/sessions/${id}`);
  return res.data.data as SessionInfo;
};

export const deleteSession = async (id: string): Promise<void> => {
  await api.delete(`/sessions/${id}`);
};

export const uploadFile = async (
  sessionId: string,
  file: File,
  onProgress?: (pct: number) => void
) => {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post(`/sessions/${sessionId}/files`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
  return res.data.data;
};

export const removeDataset = async (sessionId: string, datasetId: string): Promise<void> => {
  await api.delete(`/sessions/${sessionId}/datasets/${datasetId}`);
};

export const submitQuery = async (sessionId: string, question: string): Promise<QueryResponse> => {
  const res = await api.post(`/sessions/${sessionId}/queries`, { question });
  return res.data.data as QueryResponse;
};
