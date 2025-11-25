/**
 * EchoEventPanel Component
 *
 * DECISION CONTEXT:
 * Answers: "What exactly did our integration partner send us? What does ChainBridge see?"
 *
 * For operators/engineers:
 * - Debug webhook payloads without checking logs
 * - Verify partner integration formats before going live
 * - Reduce guesswork: see exactly what the API receives and processes
 * - Catch JSON syntax errors before hitting the backend
 *
 * UX:
 * - Client-side JSON validation (fail fast, no wasted API calls)
 * - Panel-scoped loading (doesn't block rest of dashboard)
 * - Pretty-printed responses for readability
 * - Clear error states with actionable messages
 */

import { Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { useState } from 'react';

import { apiPost } from '../lib/apiClient';

type EchoState = 'idle' | 'loading' | 'success' | 'error';

type EchoResponse = {
  original: unknown;
  processed_at: string;
  processor_id: number;
};

export function EchoEventPanel() {
  const [input, setInput] = useState('{\n  "test": "payload"\n}');
  const [state, setState] = useState<EchoState>('idle');
  const [response, setResponse] = useState<EchoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSend = async () => {
    // Reset validation error
    setValidationError(null);

    // Client-side JSON validation - fail fast
    let parsedJson: unknown;
    try {
      parsedJson = JSON.parse(input);
    } catch (err) {
      setValidationError(
        err instanceof Error ? err.message : 'Invalid JSON. Fix and retry.'
      );
      return;
    }

    // Valid JSON - proceed to API call
    setState('loading');
    setError(null);
    setResponse(null);

    try {
      const data = await apiPost<EchoResponse>('/events/echo', parsedJson);
      setResponse(data);
      setState('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send event');
      setState('error');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter to send
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 shadow-lg">
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Send className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-slate-100">Event Echo</h2>
        </div>
        <p className="text-xs text-slate-400">
          Paste event payload to verify API ingestion • Cmd+Enter to send
        </p>
      </div>

      {/* Input Section */}
      <div className="space-y-2 mb-4">
        <label className="block text-sm font-medium text-slate-300">
          JSON Payload
        </label>
        <textarea
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setValidationError(null); // Clear validation error on edit
          }}
          onKeyDown={handleKeyDown}
          className={`w-full h-32 px-3 py-2 bg-slate-950 border rounded font-mono text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none ${
            validationError ? 'border-red-500' : 'border-slate-700'
          }`}
          placeholder='{"eventType": "test", "data": {...}}'
        />

        {/* Client-side validation error */}
        {validationError && (
          <div className="flex items-start gap-2 text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span className="font-mono">{validationError}</span>
          </div>
        )}

        <button
          onClick={handleSend}
          disabled={state === 'loading'}
          className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded transition-colors text-sm font-medium flex items-center justify-center gap-2"
        >
          {state === 'loading' ? (
            <>
              <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></div>
              Sending...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Send Event
            </>
          )}
        </button>
      </div>

      {/* Response Section */}
      {(state === 'success' || state === 'error') && (
        <div className="mt-6 pt-6 border-t border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            {state === 'success' ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-medium text-emerald-400">Response</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-red-400">Error</span>
              </>
            )}
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded p-3 max-h-64 overflow-auto">
            <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap break-words">
              {state === 'success' && response
                ? JSON.stringify(response, null, 2)
                : error}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
