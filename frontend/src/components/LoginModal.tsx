import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { SessionStatus } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  session: SessionStatus | null;
  onSessionUpdated: (session: SessionStatus) => void;
}

export const LoginModal: React.FC<Props> = ({ isOpen, onClose, session, onSessionUpdated }) => {
  const [activeTab, setActiveTab] = useState<'sync' | 'token' | 'chromium'>('sync');
  const [tokenInput, setTokenInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [justConnected, setJustConnected] = useState(false);

  // Auto-close if session becomes authenticated
  useEffect(() => {
    if (session?.authenticated && isOpen) {
      setJustConnected(true);
      const timer = setTimeout(() => {
        setJustConnected(false);
        onClose();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [session?.authenticated, isOpen, onClose]);

  if (!isOpen) return null;

  const origin = window.location.origin;

  // Ultra-robust bookmarklet script
  const bookmarkletCode = `javascript:(function(){const jwtRegex=/eyJ[A-Za-z0-9_-]{10,}\\.eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]+/;let token=null;try{for(let i=0;i<localStorage.length;i++){const val=localStorage.getItem(localStorage.key(i))||'';const m=val.match(jwtRegex);if(m){token=m[0];break;}}}catch(e){}if(!token){try{for(let i=0;i<sessionStorage.length;i++){const val=sessionStorage.getItem(sessionStorage.key(i))||'';const m=val.match(jwtRegex);if(m){token=m[0];break;}}}catch(e){}}if(!token){try{const m=document.cookie.match(jwtRegex);if(m)token=m[0];}catch(e){}}if(!token){alert('No se detecto ninguna sesion activa en esta pestana de Wuolah. Por favor inicia sesion en Wuolah primero.');return;}fetch('${origin}/api/session/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(()=>{alert('¡Sesion conectada con exito a Wuolah PDF Helper! Ya puedes volver a la otra pestana.');}).catch(()=>{if(navigator.clipboard){navigator.clipboard.writeText(token).then(()=>{alert('Token copiado al portapapeles. Pegalo en la pestana Pegar Token de Wuolah PDF Helper.');}).catch(()=>{prompt('Copia tu token manualmente y pegalo en Wuolah PDF Helper:',token);});}else{prompt('Copia tu token manualmente y pegalo en Wuolah PDF Helper:',token);}});})();`;

  const handleOpenWuolahTab = () => {
    window.open('https://wuolah.com', '_blank');
  };

  const handleCopyBookmarklet = () => {
    navigator.clipboard.writeText(bookmarkletCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.setSessionToken(tokenInput.trim());
      onSessionUpdated(res);
      setJustConnected(true);
      setTimeout(() => {
        setJustConnected(false);
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Token no válido.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartChromium = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.startSession();
      onSessionUpdated(res);
      onClose();
    } catch (err: any) {
      setError(err.message || 'No se pudo abrir el navegador.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg bg-white rounded-card shadow-2xl border border-border overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-accent/10 text-accent">
              <i className="bi bi-shield-lock text-sm" />
            </div>
            <div>
              <h3 className="text-base font-bold text-ink">Conectar cuenta de Wuolah</h3>
              <p className="text-xs text-muted">Sin tocar terminales ni almacenar contraseñas</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-ink p-1 rounded-md transition-colors"
          >
            <i className="bi bi-x-lg text-sm" />
          </button>
        </div>

        {/* Success Banner if just connected */}
        {justConnected && (
          <div className="p-4 bg-surface border-b border-border text-ink text-xs font-semibold flex items-center gap-2 animate-fade-in">
            <i className="bi bi-check-circle-fill text-ink text-sm" />
            <span>¡Sesión conectada con éxito! Cerrando ventana…</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-border bg-surface px-6 pt-2 gap-2">
          <button
            type="button"
            onClick={() => { setActiveTab('sync'); setError(null); }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'sync'
                ? 'border-accent text-accent'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <i className="bi bi-lightning-charge me-1.5" />
            Sincronizar en 1 Clic
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('token'); setError(null); }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'token'
                ? 'border-accent text-accent'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <i className="bi bi-key me-1.5" />
            Pegar Token
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('chromium'); setError(null); }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'chromium'
                ? 'border-accent text-accent'
                : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <i className="bi bi-window me-1.5" />
            Ventana Chromium
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2">
              <i className="bi bi-exclamation-triangle-fill shrink-0 text-sm mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'sync' && (
            <div className="space-y-4">
              <div className="text-xs text-muted leading-relaxed">
                Ideal para <strong>Docker</strong> o despliegue en servidor. Abre Wuolah en tu navegador y transfiere tu sesión con un solo clic:
              </div>

              <div className="space-y-3">
                {/* Step 1 */}
                <div className="flex items-start gap-3 p-3.5 bg-surface border border-border rounded-xl">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">1</span>
                  <div className="flex-1 text-xs">
                    <p className="font-semibold text-ink mb-1">Abre Wuolah en una pestaña</p>
                    <p className="text-muted mb-2">Inicia sesión con tu cuenta habitual (Google, email, etc.)</p>
                    <button
                      type="button"
                      onClick={handleOpenWuolahTab}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-ink bg-white border border-border rounded-lg hover:border-ink/30 transition-all"
                    >
                      <i className="bi bi-box-arrow-up-right text-[10px]" />
                      <span>Abrir Wuolah en nueva pestaña</span>
                    </button>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="flex items-start gap-3 p-3.5 bg-surface border border-border rounded-xl">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">2</span>
                  <div className="flex-1 text-xs">
                    <p className="font-semibold text-ink mb-1">Arrastra este botón a tus Marcadores</p>
                    <p className="text-muted mb-2.5">
                      Solo tienes que arrastrarlo a la barra superior de tu navegador una única vez.
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <a
                        href={bookmarkletCode}
                        onClick={(e) => e.preventDefault()}
                        className="cursor-grab active:cursor-grabbing inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-white bg-accent rounded-lg shadow-sm hover:opacity-95 transition-all"
                        title="Arrastra este botón a tu barra de marcadores"
                      >
                        <i className="bi bi-bookmark-plus" />
                        <span>⚡ Conectar con Wuolah Helper</span>
                      </a>
                      <button
                        type="button"
                        onClick={handleCopyBookmarklet}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-ink bg-white border border-border rounded-lg hover:bg-surface transition-all"
                        title="O copia el código para ejecutarlo en la consola de Wuolah"
                      >
                        <i className={`bi ${copied ? 'bi-check-lg text-ink' : 'bi-clipboard'}`} />
                        <span>{copied ? '¡Copiado!' : 'Copiar código'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="flex items-start gap-3 p-3.5 bg-surface border border-border rounded-xl">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">3</span>
                  <div className="flex-1 text-xs">
                    <p className="font-semibold text-ink mb-0.5">Pulsa el marcador en Wuolah</p>
                    <p className="text-muted">
                      Al hacer clic en el marcador desde Wuolah, tu sesión se enviará a esta pantalla al instante y el interruptor pasará a <strong>verde (ON)</strong>.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'token' && (
            <form onSubmit={handleTokenSubmit} className="space-y-4">
              <div className="text-xs text-muted leading-relaxed">
                Si prefieres introducir tu token JWT directamente, cópialo desde tu sesión en Wuolah (en la consola con <code className="text-accent font-mono">localStorage.token</code>) y pégalo a continuación:
              </div>
              <div>
                <label className="block text-xs font-bold text-ink mb-1.5">Token JWT de Wuolah</label>
                <textarea
                  rows={3}
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
                  className="w-full text-xs font-mono p-3 bg-surface border border-border rounded-xl focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent resize-none"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-muted hover:text-ink transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading || !tokenInput.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-accent rounded-full hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  {loading ? (
                    <>
                      <i className="bi bi-arrow-repeat animate-spin text-xs" />
                      <span>Guardando…</span>
                    </>
                  ) : (
                    <span>Guardar y Conectar</span>
                  )}
                </button>
              </div>
            </form>
          )}

          {activeTab === 'chromium' && (
            <div className="space-y-4">
              <div className="text-xs text-muted leading-relaxed">
                Abre una ventana de Chromium en tu escritorio para iniciar sesión de forma interactiva.
              </div>
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2">
                <i className="bi bi-info-circle-fill shrink-0 mt-0.5" />
                <span>
                  <strong>Atención:</strong> Esta opción requiere entorno gráfico con pantalla. Si estás ejecutando la aplicación en Docker o en un servidor, utiliza la pestaña <strong>"Sincronizar en 1 Clic"</strong>.
                </span>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-muted hover:text-ink transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleStartChromium}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-ink rounded-full hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  {loading ? (
                    <>
                      <i className="bi bi-arrow-repeat animate-spin text-xs" />
                      <span>Abriendo navegador…</span>
                    </>
                  ) : (
                    <>
                      <i className="bi bi-box-arrow-in-right text-xs" />
                      <span>Abrir ventana de Chromium</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
