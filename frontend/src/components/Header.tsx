import React from 'react';

interface Props {
  onOpenArchitecture: () => void;
}

export const Header: React.FC<Props> = ({ onOpenArchitecture }) => {
  return (
    <header className="flex items-center justify-between py-5 border-b border-border">
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-ink text-white flex items-center justify-center shadow-xs">
          <i className="bi bi-file-earmark-pdf-fill text-base" />
        </div>
        <span className="font-extrabold text-ink tracking-tight text-base">
          Academic PDF Helper
        </span>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent text-white uppercase tracking-wider">
          v1.2
        </span>
      </div>

      {/* Right nav */}
      <nav className="flex items-center gap-1">
        <button
          onClick={onOpenArchitecture}
          className="px-3.5 py-2 text-xs font-semibold text-muted hover:text-ink transition-colors"
        >
          Cómo funciona
        </button>
        <a
          href="https://github.com/alvarofrancogs/academic-pdf-helper"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-muted hover:text-ink transition-colors"
        >
          <i className="bi bi-github text-sm" />
          GitHub
        </a>
      </nav>
    </header>
  );
};
