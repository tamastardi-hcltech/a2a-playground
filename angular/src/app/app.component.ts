import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { OracleApiService } from './oracle-api.service';
import { RequiredField } from './oracle.models';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'thinking';
  content: string;
  state?: string;
  progressUpdates?: string[];
  active?: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  readonly title = 'Agent Console';
  readonly subtitle =
    'Angular companion UI for the A2A workflow, with the same task lifecycle as Streamlit.';

  messages: ChatMessage[] = [];
  draftQuestion = '';
  loading = false;
  errorMessage = '';
  taskId: string | null = null;
  contextId: string | null = null;
  requiredFields: RequiredField[] = [];
  requiredFieldValues: Record<string, string> = {};
  statusLabel = 'Ready';
  private activeThinkingMessageId: string | null = null;

  private requestSequence = 0;

  constructor(private readonly oracleApi: OracleApiService) {}

  get conversationEmpty(): boolean {
    return this.messages.length === 0;
  }

  get requiredFieldsCompletedCount(): number {
    return this.requiredFields.filter((field) => !this.isRequiredFieldMissing(field.id)).length;
  }

  get requiredFieldsProgress(): number {
    if (!this.requiredFields.length) {
      return 0;
    }
    return (this.requiredFieldsCompletedCount / this.requiredFields.length) * 100;
  }

  get requiredFieldsMissingLabels(): string[] {
    return this.requiredFields
      .filter((field) => this.isRequiredFieldMissing(field.id))
      .map((field) => field.label);
  }

  roleLabel(role: ChatMessage['role']): string {
    switch (role) {
      case 'user':
        return 'You';
      case 'assistant':
        return 'Assistant';
      case 'thinking':
        return 'Working';
      default:
        return role;
    }
  }

  async submitQuestion(): Promise<void> {
    const question = this.draftQuestion.trim();
    if (!question || this.loading) {
      return;
    }

    if (!this.requiredFields.length) {
      this.taskId = null;
      this.contextId = null;
    }

    this.messages.push({
      id: this.createMessageId(),
      role: 'user',
      content: question,
    });
    this.startThinkingMessage();
    this.draftQuestion = '';
    await this.runOracleTurn(question);
  }

  onQuestionKeydown(event: KeyboardEvent): void {
    if (event.shiftKey || event.key !== 'Enter') {
      return;
    }

    if (this.loading || this.requiredFields.length > 0) {
      return;
    }

    event.preventDefault();
    void this.submitQuestion();
  }

  async submitRequiredFields(): Promise<void> {
    if (this.loading || !this.requiredFields.length) {
      return;
    }

    const missing = this.requiredFields.filter((field) => !this.requiredFieldValues[field.id]?.trim());
    if (missing.length) {
      this.errorMessage = `Please fill all required fields: ${missing.map((field) => field.label).join(', ')}`;
      this.focusFirstRequiredField(missing[0]?.id);
      return;
    }

    const followUp = this.requiredFields
      .map((field) => `${field.id}: ${this.requiredFieldValues[field.id].trim()}`)
      .join('\n');

    this.messages.push({
      id: this.createMessageId(),
      role: 'user',
      content: followUp,
    });

    this.startThinkingMessage();
    await this.runOracleTurn(followUp);
  }

  onRequiredFieldKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter') {
      return;
    }

    event.preventDefault();
    void this.submitRequiredFields();
  }

  clearError(): void {
    if (this.errorMessage) {
      this.errorMessage = '';
    }
  }

  isRequiredFieldMissing(fieldId: string): boolean {
    return !this.requiredFieldValues[fieldId]?.trim();
  }

  resetConversation(): void {
    this.messages = [];
    this.draftQuestion = '';
    this.loading = false;
    this.errorMessage = '';
    this.taskId = null;
    this.contextId = null;
    this.requiredFields = [];
    this.requiredFieldValues = {};
    this.statusLabel = 'Ready';
    this.activeThinkingMessageId = null;
  }

  private async runOracleTurn(question: string): Promise<void> {
    const token = ++this.requestSequence;
    this.loading = true;
    this.errorMessage = '';
    this.statusLabel = 'Working with agents...';

    try {
      const result = await this.oracleApi.askOrchestrator(
        question,
        this.taskId,
        this.contextId,
        (step) => this.appendThinkingStep(token, step),
      );

      if (token !== this.requestSequence) {
        return;
      }

      this.markThinkingComplete(token);

      this.messages.push({
        id: this.createMessageId(),
        role: 'assistant',
        content: result.text,
        state: result.state,
      });

      this.taskId = result.taskId;
      this.contextId = result.contextId;
      this.requiredFields = result.requiredFields;
      this.requiredFieldValues = Object.fromEntries(
        result.requiredFields.map((field) => [field.id, '']),
      );
      this.statusLabel = this.requiredFields.length
        ? 'Awaiting required input'
        : 'Ready';

      if (this.requiredFields.length) {
        this.focusFirstRequiredField();
      }
    } catch (error) {
      if (token !== this.requestSequence) {
        return;
      }

      this.markThinkingComplete(token);

      const message =
        error instanceof Error
          ? error.message
          : 'Orchestrator request failed.';
      this.errorMessage = message;
      this.messages.push({
        id: this.createMessageId(),
        role: 'assistant',
        content: message,
        state: 'failed',
      });
      this.statusLabel = 'Request failed';
    } finally {
      if (token === this.requestSequence) {
        this.loading = false;
      }
    }
  }

  private startThinkingMessage(): void {
    const messageId = this.createMessageId();
    this.activeThinkingMessageId = messageId;
    this.messages.push({
      id: messageId,
      role: 'thinking',
      content: 'Working…',
      state: 'working',
      progressUpdates: [],
      active: true,
    });
  }

  private appendThinkingStep(token: number, step: string): void {
    if (token !== this.requestSequence || !this.activeThinkingMessageId) {
      return;
    }

    const thinkingMessage = this.messages.find(
      (message) => message.id === this.activeThinkingMessageId,
    );
    if (!thinkingMessage) {
      return;
    }

    const updates = thinkingMessage.progressUpdates ?? [];
    if (updates.includes(step)) {
      return;
    }
    updates.push(step);
    thinkingMessage.progressUpdates = updates;
    thinkingMessage.content = 'Working…';
  }

  private markThinkingComplete(token: number): void {
    if (token !== this.requestSequence || !this.activeThinkingMessageId) {
      return;
    }

    const thinkingMessage = this.messages.find(
      (message) => message.id === this.activeThinkingMessageId,
    );
    if (thinkingMessage) {
      thinkingMessage.active = false;
      thinkingMessage.state = 'done';
      if (!thinkingMessage.progressUpdates?.length) {
        thinkingMessage.progressUpdates = ['The backend resolved the question.'];
      }
    }

    this.activeThinkingMessageId = null;
  }

  private createMessageId(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID();
    }
    return `msg-${Math.random().toString(16).slice(2)}-${Date.now()}`;
  }

  private focusFirstRequiredField(fieldId?: string): void {
    const targetId = fieldId ?? this.requiredFields[0]?.id;
    if (!targetId) {
      return;
    }

    window.setTimeout(() => {
      const element = document.getElementById(targetId) as HTMLInputElement | null;
      if (!element) {
        return;
      }
      element.focus();
      element.select();
    }, 0);
  }
}
