import React from 'react';

export const Hero: React.FC = () => {
  return (
    <div className="text-center pt-16 pb-12">
      <p className="text-sm text-muted font-medium tracking-wide mb-4">
        Descarga y limpieza instantánea
      </p>

      <h1 className="text-5xl sm:text-7xl font-extrabold text-ink tracking-tighter leading-[0.95] mb-6">
        WUOLAH PDF
        <br />
        HELPER
      </h1>

      <p className="text-base text-muted max-w-md mx-auto leading-relaxed mb-8">
        Obtén tus apuntes de Wuolah limpios en ~1 segundo. 
        Sin esperar 50s, sin portadas publicitarias, sin marcas de agua.
      </p>

      {/* Feature pills — Awwwards style */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        {['0s Espera', 'Sin portadas', 'Sin marcas de agua', 'XOR-27 auto-repair'].map((feat) => (
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
