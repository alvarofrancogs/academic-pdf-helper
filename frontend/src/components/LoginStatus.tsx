import React, { useState } from 'react';
import { api } from '../services/api';
import { SessionStatus } from '../types';

interface Props {
  session: SessionStatus | null;
  onSessionUpdated: (session: SessionStatus) => void;
}

export const LoginStatus: React.FC<Props> = ({ session, onSessionUpdated }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.startSession();
      onSessionUpdated(res);
    } catch (err: any) {
      setError(err.message || 'No se pudo abrir el navegador.');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.switchSession();
      onSessionUpdated(res);
    } catch (err: any) {
      setError(err.message || 'No se pudo abrir el navegador para cambiar de sesión.');
    } finally {
      setLoading(false);
    }
  };

  const isAuthenticated = Boolean(session?.authenticated);

  return (
    <div className="flex items-center justify-between py-3.5 px-4 mb-6 bg-white border border-border rounded-card">
      <div className="flex items-center gap-3.5">
        {/* Switch automático indicador de estado (Verde ON / Rojo OFF) */}
        <div
          title={isAuthenticated ? 'Sesión activa (ON)' : 'Sin sesión (OFF)'}
          className={`relative inline-flex h-6 w-12 shrink-0 items-center rounded-full transition-colors duration-300 ease-in-out ${
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
        </div>

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
          <button
            type="button"
            onClick={handleSwitchSession}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-ink bg-surface border border-border rounded-full hover:bg-white hover:border-ink/20 transition-all disabled:opacity-50"
            title="Cerrar la sesión actual e iniciar con otra cuenta"
          >
            {loading ? (
              <>
                <i className="bi bi-arrow-repeat animate-spin text-xs" />
                <span>Abriendo…</span>
              </>
            ) : (
              <>
                <i className="bi bi-arrow-left-right text-xs" />
                <span>Cambiar sesión</span>
              </>
            )}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleStartSession}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-ink bg-surface border border-border rounded-full hover:bg-white hover:border-ink/20 transition-all disabled:opacity-50"
          >
            {loading ? (
              <>
                <i className="bi bi-arrow-repeat animate-spin text-xs" />
                <span>Abriendo…</span>
              </>
            ) : (
              <>
                <span>Iniciar sesión</span>
                <i className="bi bi-box-arrow-in-right text-xs" />
              </>
            )}
          </button>
        )}
      </div>

      {error && (
        <p className="absolute text-xs text-rose-600 mt-1">{error}</p>
      )}
    </div>
  );
};
