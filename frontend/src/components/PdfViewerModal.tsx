import React, { useEffect } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  previewUrl: string;
  downloadUrl: string;
  filename: string;
  pages?: number;
}

export const PdfViewerModal: React.FC<Props> = ({
  isOpen,
  onClose,
  title,
  previewUrl,
  downloadUrl,
  filename,
  pages,
}) => {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (isOpen) {
      window.addEventListener('keydown', onKey);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm">
      <div
        className="relative w-full max-w-5xl h-[90vh] flex flex-col bg-white rounded-card shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0">
          <div className="min-w-0 pr-4">
            <p className="text-sm font-bold text-ink truncate">{title || filename}</p>
            <p className="text-xs text-muted">
              PDF limpio{pages ? ` · ${pages} páginas` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href={downloadUrl}
              download={filename}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-white bg-ink rounded-card hover:bg-black transition-colors"
            >
              <i className="bi bi-download text-xs" />
              <span>Descargar</span>
            </a>
            <button
              onClick={onClose}
              className="p-1.5 text-muted hover:text-ink transition-colors rounded-full hover:bg-surface"
              title="Cerrar (Esc)"
            >
              <i className="bi bi-x-lg text-sm" />
            </button>
          </div>
        </div>

        {/* PDF viewer */}
        <div className="flex-1 bg-surface">
          <iframe
            src={previewUrl}
            title={title}
            className="w-full h-full border-0"
          />
        </div>
      </div>
    </div>
  );
};
