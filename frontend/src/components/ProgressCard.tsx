import React, { useEffect, useState } from 'react';
import { JobStatusResponse } from '../types';

interface Props {
  job: JobStatusResponse;
}

const STEPS = [
  { label: 'Verificando sesión', minProgress: 10 },
  { label: 'Resolviendo documento', minProgress: 25 },
  { label: 'Descarga directa Fast-Path', minProgress: 50 },
  { label: 'Recibiendo archivo', minProgress: 65 },
  { label: 'Análisis de cabeceras', minProgress: 75 },
  { label: 'Limpieza PyMuPDF', minProgress: 85 },
  { label: 'Validación final', minProgress: 100 },
];

export const ProgressCard: React.FC<Props> = ({ job }) => {
  const progress = job.progress || 0;
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 100) / 10), 100);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="bg-white border border-border rounded-card p-6 mt-6">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm font-bold text-ink">Procesando documento</p>
        <div className="flex items-center gap-3 text-xs text-muted font-mono">
          <span>{elapsed.toFixed(1)}s</span>
          <span className="font-bold text-ink">{progress}%</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden mb-6">
        <div
          className="h-full bg-ink rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.max(progress, 3)}%` }}
        />
      </div>

      {/* Current step label */}
      <p className="text-xs text-muted mb-5">
        {job.message || 'Procesando…'}
      </p>

      {/* Steps checklist */}
      <div className="space-y-2.5 pt-4 border-t border-border">
        {STEPS.map((step, i) => {
          const done = progress > step.minProgress || (progress === 100 && step.minProgress === 100);
          const active =
            progress >= step.minProgress &&
            (i === STEPS.length - 1 || progress < STEPS[i + 1].minProgress);

          return (
            <div
              key={i}
              className={`flex items-center gap-3 text-xs ${
                done ? 'text-ink font-medium' : active ? 'text-accent font-semibold' : 'text-muted/50'
              }`}
            >
              <i className={`bi text-xs shrink-0 ${
                done ? 'bi-check2 text-ink font-bold' : active ? 'bi-arrow-repeat animate-spin text-accent' : 'bi-dash text-muted/30'
              }`} />
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
