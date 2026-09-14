import React, { useState } from 'react';

interface Props {
  onSubmit: (url: string) => void;
  disabled: boolean;
}

export const UrlInput: React.FC<Props> = ({ onSubmit, disabled }) => {
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateUrl = (value: string): boolean => {
    if (!value.trim()) {
      setValidationError('Introduce la URL del documento.');
      return false;
    }
    try {
      const parsed = new URL(value.trim());
      if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
        setValidationError('La URL debe comenzar con https://');
        return false;
      }
      if (!parsed.hostname.includes('wuolah.com')) {
        setValidationError('Solo se permiten enlaces de wuolah.com');
        return false;
      }
    } catch {
      setValidationError('Introduce una URL válida.');
      return false;
    }
    setValidationError(null);
    return true;
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text);
        setValidationError(null);
      }
    } catch { /* clipboard denied */ }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateUrl(url)) {
      onSubmit(url.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex items-center justify-between">
        <label htmlFor="document-url" className="text-sm font-semibold text-ink flex items-center gap-1.5">
          <i className="bi bi-link-45deg text-base" />
          <span>URL del documento</span>
        </label>
        <button
          type="button"
          onClick={handlePaste}
          disabled={disabled}
          className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline transition-colors"
        >
          <i className="bi bi-clipboard text-xs" />
          <span>Pegar del portapapeles</span>
        </button>
      </div>

      <div className="relative">
        <input
          id="document-url"
          type="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (validationError) validateUrl(e.target.value);
          }}
          placeholder="https://wuolah.com/apuntes/…"
          disabled={disabled}
          className={`w-full px-4 py-3.5 bg-white border text-ink placeholder-gray-400 text-sm rounded-card focus:outline-none focus:ring-2 transition-all ${
            validationError
              ? 'border-red-300 focus:ring-red-200'
              : 'border-border focus:ring-accent/20 focus:border-accent'
          } disabled:bg-surface disabled:text-muted`}
          autoComplete="off"
          spellCheck="false"
        />
        {url && !disabled && (
          <button
            type="button"
            onClick={() => { setUrl(''); setValidationError(null); }}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink p-1 rounded-full hover:bg-surface transition-colors"
            title="Borrar texto"
          >
            <i className="bi bi-x-lg text-xs" />
          </button>
        )}
      </div>

      {validationError && (
        <p className="text-xs text-rose-500 font-medium flex items-center gap-1">
          <i className="bi bi-exclamation-circle text-xs" />
          <span>{validationError}</span>
        </p>
      )}

      <button
        type="submit"
        disabled={disabled || !url.trim()}
        className="w-full flex items-center justify-center gap-2 py-3.5 bg-ink text-white text-sm font-bold rounded-card hover:bg-black active:scale-[0.99] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {disabled ? (
          <>
            <i className="bi bi-arrow-repeat animate-spin text-sm" />
            <span>Procesando…</span>
          </>
        ) : (
          <>
            <span>Obtener PDF limpio</span>
            <i className="bi bi-arrow-right text-sm" />
          </>
        )}
      </button>
    </form>
  );
};
