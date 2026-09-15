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
          {/* Indicador de estado */}
          <button
            type="button"
            onClick={() => {
              if (!isAuthenticated) handleOpenLogin();
            }}
            title={isAuthenticated ? 'Sesión activa' : 'Sin sesión (haz clic para conectar)'}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg border transition-all ${
              isAuthenticated
                ? 'bg-surface text-ink border-border'
                : 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100 cursor-pointer'
            }`}
          >
            {loading ? (
              <i className="bi bi-arrow-repeat animate-spin text-xs" />
            ) : isAuthenticated ? (
              <span className="w-1.5 h-1.5 rounded-full bg-ink shrink-0" />
            ) : (
              <i className="bi bi-shield-x text-rose-600 text-xs" />
            )}
            <span>{isAuthenticated ? 'Sesión activa' : 'Sin sesión'}</span>
          </button>

          <div>
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
