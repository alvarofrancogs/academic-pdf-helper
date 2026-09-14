import React from 'react';

interface Props {
  error: string;
  onRetry: () => void;
}

export const ErrorCard: React.FC<Props> = ({ error, onRetry }) => {
  return (
    <div className="bg-white border border-rose-200 rounded-card p-6 mt-6">
      <div className="flex items-center gap-2 mb-2">
        <i className="bi bi-exclamation-circle-fill text-rose-500 text-sm" />
        <p className="text-xs font-semibold text-rose-700 uppercase tracking-wider">
          Error en el procesamiento
        </p>
      </div>
      <p className="text-sm text-ink font-medium mb-4">
        {error}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-ink bg-surface border border-border rounded-card hover:bg-white transition-colors"
      >
        <i className="bi bi-arrow-clockwise text-xs" />
        <span>Intentar de nuevo</span>
      </button>
    </div>
  );
};
