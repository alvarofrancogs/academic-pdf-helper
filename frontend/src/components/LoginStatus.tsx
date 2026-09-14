import React, { useState } from 'react';
import { api } from '../services/api';
import { SessionStatus } from '../types';
import { LoginModal } from './LoginModal';

interface Props {
  session: SessionStatus | null;
  onSessionUpdated: (session: SessionStatus) => void;
}

export const LoginStatus: React.FC<Props> = ({ session, onSessionUpdated }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = Boolean(session?.authenticated);

  const handleOpenLogin = () => {
    setError(null);
    setIsModalOpen(true);
  };

  const handleClearSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.clearSession();
      onSessionUpdated(res);
    } catch (err: any) {
      setError(err.message || 'Error al cerrar sesión.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex items-center justify-between py-3.5 px-4 mb-6 bg-white border border-border rounded-card">
        <div className="flex items-center gap-3.5">
          {/* Switch automático indicador de estado (Verde ON / Rojo OFF) */}
          <button
            type="button"
            onClick={() => {
              if (!isAuthenticated) handleOpenLogin();
            }}
            title={isAuthenticated ? 'Sesión activa (ON)' : 'Sin sesión (haz clic para conectar)'}
            className={`relative inline-flex h-6 w-12 shrink-0 items-center rounded-full transition-colors duration-300 ease-in-out cursor-pointer ${
              isAuthenticated ? 'bg-emerald-500' : 'bg-rose-500'
            }`}
          >
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-md ring-0 transition-transform duration-300 ease-in-out ${
                isAuthenticated ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            >
              {loading ? (
                <i className="bi bi-arrow-repeat animate-spin text-[10px] text-ink font-bold" />
              ) : isAuthenticated ? (
                <i className="bi bi-check text-[13px] text-emerald-600 font-bold leading-none" />
              ) : (
                <i className="bi bi-x text-[13px] text-rose-600 font-bold leading-none" />
              )}
            </span>
          </button>

          <div>
            <p className="text-sm font-semibold text-ink">
              {isAuthenticated ? 'Sesión activa' : 'Sin sesión'}
            </p>
            <p className="text-xs text-muted">
              {isAuthenticated
                ? 'Descarga directa autorizada.'
                : 'Inicia sesión para descargar.'}
            </p>
          </div>
        </div>

        {/* Botones de acción */}
        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleOpenLogin}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-ink bg-surface border border-border rounded-full hover:bg-white hover:border-ink/20 transition-all disabled:opacity-50"
                title="Cambiar o renovar token de Wuolah"
              >
                <i className="bi bi-arrow-repeat text-xs" />
                <span>Cambiar</span>
              </button>
              <button
                type="button"
                onClick={handleClearSession}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-muted bg-white border border-border rounded-full hover:text-rose-600 hover:border-rose-200 transition-all disabled:opacity-50"
                title="Desconectar cuenta"
              >
                <i className="bi bi-box-arrow-right text-xs" />
                <span>Salir</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleOpenLogin}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-ink bg-surface border border-border rounded-full hover:bg-white hover:border-ink/20 transition-all disabled:opacity-50 shadow-sm"
            >
              <span>Iniciar sesión</span>
              <i className="bi bi-box-arrow-in-right text-xs" />
            </button>
          )}
        </div>

        {error && (
          <p className="absolute text-xs text-rose-600 mt-1">{error}</p>
        )}
      </div>

      {/* Modal de Conexión de Sesión */}
      <LoginModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        session={session}
        onSessionUpdated={onSessionUpdated}
      />
    </>
  );
};
