/**
 * Investigation input with spirit-companion prefix detection.
 *
 * Messages starting with "Matthew," route to spirit companion chat.
 * All other messages go to the narrator.
 */

import { useState, useCallback, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useTheme } from '../context/useTheme';
import { isMatthewMessage, stripMatthewPrefix } from '../utils/matthewInput';

interface MatthewChatInputProps {
  onMatthewMessage: (message: string) => void;
  onNarratorMessage: (message: string) => void;
  disabled?: boolean;
  matthewLoading?: boolean;
  narratorLoading?: boolean;
  placeholder?: string;
  className?: string;
}

export const MatthewChatInput = forwardRef<HTMLTextAreaElement, MatthewChatInputProps>(
  (
    {
      onMatthewMessage,
      onNarratorMessage,
      disabled = false,
      matthewLoading = false,
      narratorLoading = false,
      placeholder = "> Type actions or 'Matthew, <question>' to consult your spirit companion...",
      className = '',
    },
    ref
  ) => {
    const { theme } = useTheme();
    const [input, setInput] = useState('');
    const [isVoiceTarget, setIsVoiceTarget] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useImperativeHandle(ref, () => textareaRef.current!, []);

    useEffect(() => {
      setIsVoiceTarget(isMatthewMessage(input));
    }, [input]);

    const handleSubmit = useCallback(
      (e: React.FormEvent) => {
        e.preventDefault();

        const trimmedInput = input.trim();
        if (!trimmedInput) return;

        if (isMatthewMessage(trimmedInput)) {
          const message = stripMatthewPrefix(trimmedInput);
          if (message) {
            onMatthewMessage(message);
          }
        } else {
          onNarratorMessage(trimmedInput);
        }

        setInput('');
        setIsVoiceTarget(false);
      },
      [input, onMatthewMessage, onNarratorMessage]
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey && !disabled) {
          e.preventDefault();
          handleSubmit(e);
        }
      },
      [handleSubmit, disabled]
    );

    const isLoading = matthewLoading || narratorLoading || disabled;

    return (
      <form onSubmit={handleSubmit} className={`space-y-2 ${className}`}>
        <div className="flex items-center justify-between">
          <label
            htmlFor="action-input"
            className="block text-xs text-gray-500 uppercase tracking-wider"
          >
            What do you do?
          </label>
          {isVoiceTarget && (
            <span className="text-xs text-amber-400 font-sans animate-pulse">
              Consulting Matthew...
            </span>
          )}
        </div>

        <textarea
          ref={textareaRef}
          id="action-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={3}
          disabled={isLoading}
          className={`
            w-full bg-gray-900 text-gray-100 border rounded-sm p-3
            placeholder-gray-600 focus:outline-none resize-none
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors duration-200 text-sm font-sans tracking-wide
            ${isVoiceTarget
              ? 'border-amber-600/50 focus:border-amber-500 focus:bg-gray-800'
              : 'border-gray-600 focus:border-gray-400 focus:bg-gray-800'
            }
          `}
          aria-label="Enter your investigation action or consult Matthew"
        />

        <div className="flex items-center justify-between text-xs">
          <div className="text-gray-500">
            <span>Press Ctrl+Enter to submit</span>
            {!isVoiceTarget && (
              <span className="ml-2 text-amber-500/70">
                | Prefix with &quot;Matthew,&quot; to consult your spirit companion
              </span>
            )}
          </div>

          {matthewLoading && (
            <span className={`flex items-center text-amber-400 ${theme.fonts.ui}`}>
              <span className="animate-spin mr-2">*</span>
              Matthew is thinking...
            </span>
          )}
          {narratorLoading && !matthewLoading && (
            <span className={`flex items-center text-green-400 ${theme.fonts.ui}`}>
              <span className="animate-spin mr-2">*</span>
              Investigating...
            </span>
          )}
        </div>
      </form>
    );
  }
);

MatthewChatInput.displayName = 'MatthewChatInput';