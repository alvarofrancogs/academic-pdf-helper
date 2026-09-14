export type AppState =
  | 'IDLE'
  | 'STARTING_BROWSER'
  | 'LOGIN_REQUIRED'
  | 'AUTHENTICATED'
  | 'OPENING_DOCUMENT'
  | 'ANALYZING_NETWORK'
  | 'DOWNLOADING'
  | 'ANALYZING_FILE'
  | 'PROCESSING'
  | 'VALIDATING'
  | 'READY'
  | 'ERROR';

export interface ResultMetadata {
  pages: number;
  size_bytes: number;
  size_formatted: string;
  pdf_version: string;
  detected_type?: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  filename?: string | null;
  result_metadata?: ResultMetadata | null;
  error?: string | null;
}

export interface SessionStatus {
  authenticated: boolean;
  browser_running: boolean;
  message: string;
}

export interface ProcessResponse {
  job_id: string;
  status: string;
}

export interface HistoryItem {
  id: string;
  jobId: string;
  url: string;
  filename: string;
  pages: number;
  sizeFormatted: string;
  timestamp: number;
  pdfVersion?: string;
  detectedType?: string;
}

