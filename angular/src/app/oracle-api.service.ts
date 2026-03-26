import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import {
  DataPart,
  JsonRpcRequest,
  JsonRpcResponse,
  OracleChatResponse,
  OracleMessage,
  OraclePart,
  OracleTask,
  RequiredField,
  TextPart,
} from './oracle.models';

const API_BASE_URL = '/api';
const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 120000;

interface TaskSnapshot {
  text: string;
  state: string;
  taskId: string;
  contextId: string;
  requiredFields: RequiredField[];
}

@Injectable({ providedIn: 'root' })
export class OracleApiService {
  constructor(private readonly http: HttpClient) {}

  async askOrchestrator(
    question: string,
    taskId: string | null,
    contextId: string | null,
    onProgress?: (step: string) => void,
  ): Promise<OracleChatResponse> {
    const requestMessage: OracleMessage = {
      kind: 'message',
      message_id: this.createId(),
      role: 'user',
      task_id: taskId ?? undefined,
      context_id: contextId ?? undefined,
      parts: [
        {
          kind: 'text',
          text: question,
        },
      ],
    };

    const sendResponse = await this.postJsonRpc<OracleTask | OracleMessage>(
      'message/send',
      {
        message: requestMessage,
        configuration: {
          blocking: false,
        },
      },
    );

    const initial = this.normalizeResponse(sendResponse.result);
    if (!initial) {
      throw new Error('The orchestrator returned an empty response.');
    }

    if (this.isMessage(initial)) {
      return {
        text: this.extractTextFromMessage(initial) || 'No response text returned.',
        state: 'completed',
        taskId: initial.task_id ?? taskId,
        contextId: initial.context_id ?? contextId,
        requiredFields: [],
        progressUpdates: [],
      };
    }

    let snapshot = this.snapshotFromTask(initial);
    const progressUpdates: string[] = [];
    const seenUpdates = new Set<string>();

    const emitProgress = (step: string) => {
      const trimmed = step.trim();
      if (!trimmed || seenUpdates.has(trimmed)) {
        return;
      }
      seenUpdates.add(trimmed);
      progressUpdates.push(trimmed);
      onProgress?.(trimmed);
    };

    if (snapshot.state === 'working' && snapshot.text) {
      emitProgress(snapshot.text);
    }

    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (this.shouldPoll(snapshot.state) && Date.now() < deadline) {
      await this.delay(POLL_INTERVAL_MS);
      const polled = await this.fetchTask(snapshot.taskId);
      snapshot = this.snapshotFromTask(polled);
      if (snapshot.text) {
        emitProgress(snapshot.text);
      }
    }

    return {
      text: snapshot.text || 'No response text returned.',
      state: snapshot.state,
      taskId: snapshot.taskId,
      contextId: snapshot.contextId,
      requiredFields: snapshot.requiredFields,
      progressUpdates,
    };
  }

  private async fetchTask(taskId: string): Promise<OracleTask> {
    const response = await this.postJsonRpc<OracleTask>('tasks/get', {
      id: taskId,
    });
    const result = this.normalizeResponse(response.result);
    if (!result || this.isMessage(result)) {
      throw new Error('The orchestrator returned an invalid task payload.');
    }
    return result;
  }

  private snapshotFromTask(task: OracleTask): TaskSnapshot {
    return {
      text: this.extractTextFromTask(task),
      state: task.status?.state ?? 'unknown',
      taskId: task.id,
      contextId: task.context_id,
      requiredFields: this.extractRequiredFields(task),
    };
  }

  private async postJsonRpc<T>(
    method: string,
    params: Record<string, unknown>,
  ): Promise<JsonRpcResponse<T>> {
    const payload: JsonRpcRequest<Record<string, unknown>> = {
      jsonrpc: '2.0',
      id: this.createId(),
      method,
      params,
    };

    return firstValueFrom(
      this.http.post<JsonRpcResponse<T>>(`${API_BASE_URL}/`, payload),
    );
  }

  private normalizeResponse<T>(
    result: T | JsonRpcResponse<T> | null | undefined,
  ): T | null {
    if (!result) {
      return null;
    }
    if (typeof result === 'object' && 'result' in result) {
      return (result as JsonRpcResponse<T>).result ?? null;
    }
    return result as T;
  }

  private extractTextFromTask(task: OracleTask): string {
    const current = task.status?.message
      ? this.extractTextFromMessage(task.status.message)
      : '';
    if (current) {
      return current;
    }

    const history = task.history ?? [];
    for (let index = history.length - 1; index >= 0; index -= 1) {
      const entry = history[index];
      if (entry.role !== 'agent') {
        continue;
      }
      const text = this.extractTextFromMessage(entry);
      if (text) {
        return text;
      }
    }
    return '';
  }

  private extractTextFromMessage(message: OracleMessage): string {
    return (message.parts ?? [])
      .map((part) => this.textFromPart(part))
      .filter((part): part is string => Boolean(part))
      .join('\n')
      .trim();
  }

  private extractRequiredFields(task: OracleTask): RequiredField[] {
    const parts = task.status?.message?.parts ?? [];
    for (const part of parts) {
      if (!this.isDataPart(part)) {
        continue;
      }
      const data = part.data as Record<string, unknown>;
      if (data['type'] !== 'input_required') {
        continue;
      }
      const requiredFields = data['required_fields'];
      if (!Array.isArray(requiredFields)) {
        continue;
      }
      return requiredFields.filter(
        (field): field is RequiredField => this.isRequiredField(field),
      );
    }
    return [];
  }

  private textFromPart(part: OraclePart): string | null {
    if (this.isTextPart(part)) {
      return part.text;
    }
    return null;
  }

  private shouldPoll(state: string): boolean {
    return state === 'working' || state === 'submitted' || state === 'unknown';
  }

  private isMessage(value: OracleTask | OracleMessage): value is OracleMessage {
    return Boolean((value as OracleMessage).message_id);
  }

  private isDataPart(part: OraclePart): part is DataPart {
    return (
      typeof part === 'object' &&
      part !== null &&
      'kind' in part &&
      (part as DataPart).kind === 'data' &&
      'data' in part
    );
  }

  private isTextPart(part: OraclePart): part is TextPart {
    return (
      typeof part === 'object' &&
      part !== null &&
      'kind' in part &&
      (part as TextPart).kind === 'text' &&
      'text' in part
    );
  }

  private isRequiredField(value: unknown): value is RequiredField {
    if (typeof value !== 'object' || value === null) {
      return false;
    }
    const candidate = value as RequiredField;
    return typeof candidate.id === 'string' && typeof candidate.label === 'string';
  }

  private createId(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID();
    }
    return `oracle-${Math.random().toString(16).slice(2)}-${Date.now()}`;
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(resolve, ms);
    });
  }
}
