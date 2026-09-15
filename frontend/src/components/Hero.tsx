import React from 'react';

export const Hero: React.FC = () => {
  return (
    <div className="text-center pt-16 pb-12">
      <p className="text-sm text-muted font-medium tracking-wide mb-4">
        Descarga y limpieza automatizada
      </p>

      <h1 className="text-5xl sm:text-7xl font-extrabold text-ink tracking-tighter leading-[0.95] mb-6">
        WUOLAH PDF
        <br />
        HELPER
      </h1>

      <p className="text-base text-muted max-w-md mx-auto leading-relaxed mb-8">
        Obtén tus apuntes de Wuolah limpios y sin publicidad.
        Sin portadas promocionales, sin marcas de agua, sin esperas manuales.
      </p>

      {/* Feature pills — Awwwards style */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        {['Descarga automática', 'Sin portadas', 'Sin marcas de agua', 'XOR-27 auto-repair'].map((feat) => (
          <span
            key={feat}
            className="px-3.5 py-1.5 text-xs font-semibold text-ink bg-white border border-border rounded-full"
          >
            {feat}
          </span>
        ))}
      </div>
    </div>
  );
};
