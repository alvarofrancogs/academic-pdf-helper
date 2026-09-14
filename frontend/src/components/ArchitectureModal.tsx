import React from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchitectureModal: React.FC<Props> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const steps = [
    {
      num: '01',
      title: 'Fast-Path Direct API',
      desc: 'El timer de 50s de Wuolah es cosmético. Llamamos directamente a POST /v2/download con avoidFallback: true y el token de sesión, obteniendo la URL del PDF en <1.2s.',
    },
    {
      num: '02',
      title: 'PyMuPDF Clean Engine',
      desc: 'Eliminamos la portada publicitaria de Wuolah (página 1) y redactamos marcas de agua de margen con PyMuPDF, dejando solo el contenido académico original.',
    },
    {
      num: '03',
      title: 'Desofuscación XOR-27',
      desc: 'Algunos PDFs de Wuolah tienen la cabecera enmascarada con XOR key=27. Nuestro normalizador detecta y restaura la firma %PDF- automáticamente.',
    },
    {
      num: '04',
      title: 'Playwright Session Fallback',
      desc: 'Para autenticación inicial, Chromium headless gestiona cookies y almacenamiento local de forma segura, sin exponer credenciales.',
    },
  ];

  const techs = ['FastAPI', 'Python', 'PyMuPDF', 'Playwright', 'React 18', 'TypeScript', 'Vite', 'Docker'];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-white rounded-card overflow-hidden shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div>
            <h3 className="text-base font-extrabold text-ink">Cómo funciona</h3>
            <p className="text-xs text-muted mt-0.5">Pipeline de procesamiento en ~1 segundo</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-muted hover:text-ink transition-colors rounded-full hover:bg-surface"
            title="Cerrar"
          >
            <i className="bi bi-x-lg text-sm" />
          </button>
        </div>

        {/* Steps */}
        <div className="px-6 py-5 space-y-5 max-h-[60vh] overflow-y-auto">
          {steps.map((step) => (
            <div key={step.num} className="flex gap-4">
              <span className="text-3xl font-extrabold text-border leading-none shrink-0">
                {step.num}
              </span>
              <div>
                <h4 className="text-sm font-bold text-ink">{step.title}</h4>
                <p className="text-xs text-muted leading-relaxed mt-1">{step.desc}</p>
              </div>
            </div>
          ))}

          {/* Tech stack */}
          <div className="pt-4 border-t border-border">
            <p className="text-[11px] font-bold uppercase tracking-wider text-muted mb-2">
              Stack
            </p>
            <div className="flex flex-wrap gap-1.5">
              {techs.map((t) => (
                <span
                  key={t}
                  className="px-2.5 py-1 text-[11px] font-semibold text-ink bg-surface border border-border rounded-full"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-surface border-t border-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-white bg-ink rounded-card hover:bg-black transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
