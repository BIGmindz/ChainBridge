/**
 * ApprovalConfirmation — HAM v1
 *
 * Two-step explicit confirmation for human approval.
 * Step 1: Checkbox acknowledgment
 * Step 2: Typed confirmation phrase (case-sensitive)
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Check, AlertCircle, KeyRound } from 'lucide-react';
import {
  REQUIRED_CONFIRMATION_PHRASE,
  isConfirmationValid,
} from '../../types/approval';

interface Props {
  /** Whether the checkbox is checked */
  checkboxChecked: boolean;
  /** Callback when checkbox changes */
  onCheckboxChange: (checked: boolean) => void;
  /** Current typed confirmation value */
  typedConfirmation: string;
  /** Callback when typed confirmation changes */
  onTypedConfirmationChange: (value: string) => void;
  /** Whether the form is disabled (e.g., during submission) */
  disabled?: boolean;
}

/**
 * Two-step confirmation component for human approval.
 *
 * Step 1: User must check the acknowledgment checkbox.
 * Step 2: User must type the exact phrase "AUTHORIZE" (case-sensitive).
 *
 * No autofill, no shortcuts, no keyboard-only confirmation for destructive actions.
 */
export function ApprovalConfirmation({
  checkboxChecked,
  onCheckboxChange,
  typedConfirmation,
  onTypedConfirmationChange,
  disabled = false,
}: Props): JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputFocused, setInputFocused] = useState(false);

  // Focus the input when checkbox is checked
  useEffect(() => {
    if (checkboxChecked && inputRef.current && !disabled) {
      inputRef.current.focus();
    }
  }, [checkboxChecked, disabled]);

  const handleCheckboxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!disabled) {
        onCheckboxChange(e.target.checked);
      }
    },
    [disabled, onCheckboxChange]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!disabled) {
        // Prevent paste — require manual typing
        onTypedConfirmationChange(e.target.value);
      }
    },
    [disabled, onTypedConfirmationChange]
  );

  // Block paste to require manual typing
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
  }, []);

  // Block autocomplete
  const handleAutocomplete = useCallback((e: React.FormEvent) => {
    e.preventDefault();
  }, []);

  const isTypedValid = isConfirmationValid(typedConfirmation);
  const showTypedError =
    typedConfirmation.length > 0 && !isTypedValid && !inputFocused;

  return (
    <div className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4">
      {/* Step 1: Checkbox */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-700 text-slate-300">
            1
          </span>
          <span>Acknowledgment</span>
        </div>

        <label
          className={`
            flex cursor-pointer items-start gap-3 rounded-md border p-3
            transition-colors
            ${disabled ? 'cursor-not-allowed opacity-50' : 'hover:bg-slate-800/50'}
            ${checkboxChecked ? 'border-emerald-500/50 bg-emerald-950/20' : 'border-slate-700'}
          `}
        >
          <div className="relative mt-0.5">
            <input
              type="checkbox"
              checked={checkboxChecked}
              onChange={handleCheckboxChange}
              disabled={disabled}
              className="sr-only"
              aria-describedby="checkbox-description"
            />
            <div
              className={`
                flex h-5 w-5 items-center justify-center rounded border-2 transition-colors
                ${
                  checkboxChecked
                    ? 'border-emerald-500 bg-emerald-500'
                    : 'border-slate-500 bg-slate-800'
                }
                ${disabled ? '' : 'group-hover:border-slate-400'}
              `}
            >
              {checkboxChecked && <Check className="h-3 w-3 text-white" />}
            </div>
          </div>
          <span id="checkbox-description" className="text-sm text-slate-200">
            I have reviewed this action and understand its impact
          </span>
        </label>
      </div>

      {/* Step 2: Typed Confirmation */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
          <span
            className={`
              flex h-5 w-5 items-center justify-center rounded-full text-slate-300
              ${checkboxChecked ? 'bg-slate-700' : 'bg-slate-800 text-slate-500'}
            `}
          >
            2
          </span>
          <span className={checkboxChecked ? '' : 'text-slate-500'}>
            Type Confirmation
          </span>
        </div>

        <div
          className={`
            rounded-md border p-3 transition-colors
            ${!checkboxChecked ? 'opacity-50' : ''}
            ${
              isTypedValid
                ? 'border-emerald-500/50 bg-emerald-950/20'
                : showTypedError
                  ? 'border-red-500/50 bg-red-950/20'
                  : 'border-slate-700'
            }
          `}
        >
          <div className="flex items-center gap-3">
            <KeyRound
              className={`h-5 w-5 ${isTypedValid ? 'text-emerald-400' : 'text-slate-500'}`}
            />
            <div className="flex-1">
              <label className="block text-xs text-slate-400">
                Type <span className="font-mono font-bold text-slate-200">AUTHORIZE</span> to
                confirm
              </label>
              <input
                ref={inputRef}
                type="text"
                value={typedConfirmation}
                onChange={handleInputChange}
                onPaste={handlePaste}
                onBeforeInput={handleAutocomplete}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                disabled={disabled || !checkboxChecked}
                placeholder="Type confirmation..."
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                data-form-type="other"
                data-lpignore="true"
                className={`
                  mt-1 w-full rounded border bg-slate-950 px-3 py-2 font-mono text-sm
                  placeholder:text-slate-600
                  focus:outline-none focus:ring-2
                  ${
                    isTypedValid
                      ? 'border-emerald-500 text-emerald-300 focus:ring-emerald-500/50'
                      : showTypedError
                        ? 'border-red-500 text-red-300 focus:ring-red-500/50'
                        : 'border-slate-700 text-slate-200 focus:ring-slate-500/50'
                  }
                  disabled:cursor-not-allowed disabled:opacity-50
                `}
                aria-label="Type AUTHORIZE to confirm"
                aria-invalid={showTypedError}
              />
            </div>
          </div>

          {/* Validation feedback */}
          {showTypedError && (
            <div className="mt-2 flex items-center gap-2 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              <span>
                Confirmation must be exactly "{REQUIRED_CONFIRMATION_PHRASE}" (case-sensitive)
              </span>
            </div>
          )}

          {isTypedValid && (
            <div className="mt-2 flex items-center gap-2 text-xs text-emerald-400">
              <Check className="h-3 w-3" />
              <span>Confirmation valid</span>
            </div>
          )}
        </div>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center justify-center gap-2 pt-2">
        <div
          className={`h-2 w-2 rounded-full ${checkboxChecked ? 'bg-emerald-500' : 'bg-slate-600'}`}
        />
        <div className={`h-2 w-2 rounded-full ${isTypedValid ? 'bg-emerald-500' : 'bg-slate-600'}`} />
      </div>
    </div>
  );
}
