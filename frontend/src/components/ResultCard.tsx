import React, { useState } from 'react';
import { JobStatusResponse } from '../types';
import { api } from '../services/api';

interface Props {
  job: JobStatusResponse;
  onReset: () => void;
  onPreview: () => void;
}

export const ResultCard: React.FC<Props> = ({ job, onReset, onPreview }) => {
  const [copied, setCopied] = useState(false);
  const metadata = job.result_metadata;
  const downloadUrl = api.getDownloadUrl(job.job_id);
  const filename = job.filename || 'documento_wuolah.pdf';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${downloadUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* */ }
  };

  return (
    <div className="bg-white border border-border rounded-card p-6 mt-6">
      {/* Success header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
            Documento listo
          </p>
        </div>
        <h2 className="text-xl font-extrabold text-ink tracking-tight truncate">
          {filename}
        </h2>
        <p className="text-sm text-muted mt-1">
          PDF limpio y normalizado, sin publicidad ni marcas.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-px bg-border rounded-card overflow-hidden mb-6">
        <div className="bg-white p-4 text-center">
          <p className="text-2xl font-extrabold text-ink">{metadata?.pages ?? 0}</p>
          <p className="text-[11px] text-muted font-medium mt-0.5">Páginas</p>
        </div>
        <div className="bg-white p-4 text-center">
          <p className="text-2xl font-extrabold text-ink">{metadata?.size_formatted ?? '—'}</p>
          <p className="text-[11px] text-muted font-medium mt-0.5">Tamaño</p>
        </div>
        <div className="bg-white p-4 text-center">
          <p className="text-2xl font-extrabold text-accent">0</p>
          <p className="text-[11px] text-muted font-medium mt-0.5">Anuncios</p>
        </div>
      </div>

      {metadata?.detected_type === 'wuolah_xor_obfuscated' && (
        <p className="text-xs text-muted bg-surface border border-border rounded-card px-4 py-2.5 mb-6 flex items-center gap-2">
          <i className="bi bi-shield-check text-emerald-600 text-sm" />
          <span>Cabecera XOR-27 reparada automáticamente</span>
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-3 mb-4">
        <a
          href={downloadUrl}
          download={filename}
          className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-ink text-white text-sm font-bold rounded-card hover:bg-black active:scale-[0.99] transition-all"
        >
          <i className="bi bi-download text-sm" />
          <span>Descargar PDF</span>
        </a>
        <button
          type="button"
          onClick={onPreview}
          className="flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-bold text-ink bg-white border border-border rounded-card hover:bg-surface active:scale-[0.99] transition-all"
        >
          <i className="bi bi-eye text-sm" />
          <span>Previsualizar</span>
        </button>
      </div>

      {/* Secondary links */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink transition-colors"
        >
          {copied ? (
            <>
              <i className="bi bi-check2 text-emerald-600 text-xs" />
              <span className="text-emerald-700 font-semibold">Enlace copiado</span>
            </>
          ) : (
            <>
              <i className="bi bi-link-45deg text-xs" />
              <span>Copiar enlace</span>
            </>
          )}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline transition-colors"
        >
          <span>Procesar otro</span>
          <i className="bi bi-arrow-right text-xs" />
        </button>
      </div>
    </div>
  );
};
