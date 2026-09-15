import React from 'react';
import { HistoryItem } from '../types';
import { api } from '../services/api';

interface Props {
  items: HistoryItem[];
  onSelectItem: (item: HistoryItem) => void;
  onRemoveItem: (id: string) => void;
  onClearHistory: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const HistoryDrawer: React.FC<Props> = ({
  items,
  onSelectItem,
  onRemoveItem,
  onClearHistory,
  isOpen,
  onToggle,
}) => {
  if (items.length === 0) return null;

  return (
    <div className="mt-6">
      <button
        type="button"
        onClick={onToggle}
        className="group w-full flex items-center justify-between py-3 text-xs font-semibold text-muted hover:text-ink transition-colors select-none"
      >
        <span className="flex items-center gap-2">
          <i className="bi bi-clock-history text-xs text-muted group-hover:text-ink transition-colors" />
          <span>Historial reciente ({items.length})</span>
        </span>
        <span
          className={`w-5 h-5 rounded-full border flex items-center justify-center transition-all duration-300 ease-out ${
            isOpen
              ? 'bg-ink text-white border-ink rotate-180'
              : 'bg-surface text-muted border-border group-hover:border-ink/30 group-hover:text-ink rotate-0'
          }`}
          title={isOpen ? 'Contraer historial' : 'Desplegar historial'}
        >
          <i className={`bi ${isOpen ? 'bi-dash' : 'bi-plus'} text-xs leading-none transition-transform duration-300`} />
        </span>
      </button>

      <div
        className={`grid transition-all duration-300 ease-out ${
          isOpen ? 'grid-rows-[1fr] opacity-100 mt-1 mb-2' : 'grid-rows-[0fr] opacity-0 my-0 pointer-events-none'
        }`}
      >
        <div className="overflow-hidden space-y-1 pb-1">
          {items.map((item) => {
            const time = new Date(item.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            });

            return (
              <div
                key={item.id}
                className="flex items-center justify-between gap-3 py-2.5 px-3 bg-white border border-border rounded-card text-xs hover:border-ink/20 transition-all"
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <div className="w-7 h-7 rounded-md bg-surface text-ink flex items-center justify-center shrink-0 border border-border">
                    <i className="bi bi-file-earmark-pdf text-sm" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-ink truncate">{item.filename}</p>
                    <p className="text-muted">
                      {item.pages} págs · {item.sizeFormatted} · {time}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => onSelectItem(item)}
                    className="flex items-center gap-1 text-muted hover:text-ink transition-colors px-1.5 py-1 rounded"
                    title="Previsualizar"
                  >
                    <i className="bi bi-eye text-xs" />
                    <span>Ver</span>
                  </button>
                  <a
                    href={api.getDownloadUrl(item.jobId)}
                    download={item.filename}
                    className="flex items-center text-accent hover:text-accent/80 transition-colors p-1"
                    title="Descargar"
                  >
                    <i className="bi bi-download text-xs" />
                  </a>
                  <button
                    onClick={() => onRemoveItem(item.id)}
                    className="flex items-center text-muted hover:text-rose-600 transition-colors p-1"
                    title="Eliminar del historial"
                  >
                    <i className="bi bi-x-lg text-[10px]" />
                  </button>
                </div>
              </div>
            );
          })}

          <button
            onClick={onClearHistory}
            className="w-full flex items-center justify-center gap-1.5 text-center text-xs text-muted hover:text-rose-600 py-2 transition-colors mt-2"
          >
            <i className="bi bi-trash3 text-xs" />
            <span>Borrar historial</span>
          </button>
        </div>
      </div>
    </div>
  );
};
