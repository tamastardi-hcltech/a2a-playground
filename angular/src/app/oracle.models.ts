export interface JsonRpcRequest<P> {
  jsonrpc: '2.0';
  id: string;
  method: string;
  params: P;
}

export interface JsonRpcError {
  code: number;
  message?: string;
  data?: unknown;
}

export interface JsonRpcResponse<T> {
  jsonrpc: '2.0';
  id?: string | number | null;
  result?: T;
  error?: JsonRpcError;
}

export interface TextPart {
  kind: 'text';
  text: string;
  metadata?: Record<string, unknown> | null;
}

export interface DataPart {
  kind: 'data';
  data: Record<string, unknown>;
  metadata?: Record<string, unknown> | null;
}

export type OraclePart = TextPart | DataPart | Record<string, unknown>;

export interface OracleMessage {
  kind?: 'message';
  message_id: string;
  role: string;
  parts: OraclePart[];
  context_id?: string | null;
  task_id?: string | null;
}

export interface OracleTaskStatus {
  state: string;
  message?: OracleMessage | null;
  timestamp?: string | null;
}

export interface OracleTask {
  kind?: 'task';
  id: string;
  context_id: string;
  history?: OracleMessage[] | null;
  status: OracleTaskStatus;
}

export interface RequiredField {
  id: string;
  label: string;
  format?: string;
  example?: string;
}

export interface OracleChatResponse {
  text: string;
  state: string;
  taskId: string | null;
  contextId: string | null;
  requiredFields: RequiredField[];
  progressUpdates: string[];
}
