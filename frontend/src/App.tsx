import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { LoginStatus } from './components/LoginStatus';
import { UrlInput } from './components/UrlInput';
import { ProgressCard } from './components/ProgressCard';
import { ResultCard } from './components/ResultCard';
import { ErrorCard } from './components/ErrorCard';
import { HistoryDrawer } from './components/HistoryDrawer';
import { ArchitectureModal } from './components/ArchitectureModal';
import { PdfViewerModal } from './components/PdfViewerModal';
import { api } from './services/api';
import { JobStatusResponse, SessionStatus, HistoryItem } from './types';

export function App() {
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [currentJob, setCurrentJob] = useState<JobStatusResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);

  // History
  const [history, setHistory] = useState<HistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('wuolah_history');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Modals
  const [isArchOpen, setIsArchOpen] = useState(false);
  const [previewModal, setPreviewModal] = useState({
    isOpen: false, title: '', previewUrl: '', downloadUrl: '', filename: '', pages: undefined as number | undefined,
  });

  // Persist history
  useEffect(() => {
    try { localStorage.setItem('wuolah_history', JSON.stringify(history)); } catch { /* */ }
  }, [history]);

  // Automatic session detection
  useEffect(() => {
    const refreshSession = () => {
      api.getSessionStatus().then(setSession).catch(() => {});
    };

    refreshSession();
    window.addEventListener('focus', refreshSession);
    const timer = setInterval(refreshSession, 4000);

    return () => {
      window.removeEventListener('focus', refreshSession);
      clearInterval(timer);
    };
  }, []);

  // Job polling
  useEffect(() => {
    if (!currentJob || currentJob.status === 'ready' || currentJob.status === 'error') {
      if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
      return;
    }

    const check = async () => {
      try {
        const updated = await api.getJobStatus(currentJob.job_id);
        setCurrentJob(updated);
        if (updated.status === 'ready') {
          setIsProcessing(false);
          if (updated.filename) {
            const item: HistoryItem = {
              id: `${updated.job_id}-${Date.now()}`,
              jobId: updated.job_id,
              url: '',
              filename: updated.filename,
              pages: updated.result_metadata?.pages || 1,
              sizeFormatted: updated.result_metadata?.size_formatted || '—',
              timestamp: Date.now(),
              pdfVersion: updated.result_metadata?.pdf_version,
              detectedType: updated.result_metadata?.detected_type,
            };
            setHistory((prev) => [item, ...prev.filter((p) => p.jobId !== updated.job_id)].slice(0, 20));
          }
        } else if (updated.status === 'error') {
          setIsProcessing(false);
          setError(updated.error || 'Error al procesar.');
        }
      } catch (err: any) {
        setIsProcessing(false);
        setError(err.message || 'Error de conexión.');
      }
    };

    pollingRef.current = window.setInterval(check, 1000);
    return () => { if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; } };
  }, [currentJob?.job_id, currentJob?.status]);

  const handleSubmit = async (url: string) => {
    setError(null);
    setIsProcessing(true);
    setCurrentJob(null);
    try {
      const res = await api.processDocument(url);
      setCurrentJob({ job_id: res.job_id, status: res.status, progress: 10, message: 'Iniciando descarga directa…' });
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || 'No se pudo iniciar.');
    }
  };

  const handleReset = () => { setCurrentJob(null); setIsProcessing(false); setError(null); };

  const openPreviewCurrent = () => {
    if (!currentJob) return;
    setPreviewModal({
      isOpen: true,
      title: currentJob.filename || 'Documento',
      previewUrl: api.getPreviewUrl(currentJob.job_id),
      downloadUrl: api.getDownloadUrl(currentJob.job_id),
      filename: currentJob.filename || 'documento.pdf',
      pages: currentJob.result_metadata?.pages,
    });
  };

  const openPreviewHistory = (item: HistoryItem) => {
    setPreviewModal({
      isOpen: true, title: item.filename,
      previewUrl: api.getPreviewUrl(item.jobId),
      downloadUrl: api.getDownloadUrl(item.jobId),
      filename: item.filename, pages: item.pages,
    });
  };

  return (
    <div className="min-h-screen bg-surface">
      {/* Full-width header */}
      <div className="max-w-5xl mx-auto px-5 sm:px-8">
        <Header onOpenArchitecture={() => setIsArchOpen(true)} />
      </div>

      {/* Centered content */}
      <div className="max-w-xl mx-auto px-5 sm:px-8">
        <Hero />

        {/* Main content card */}
        <div className="bg-white border border-border rounded-card p-6 sm:p-8 shadow-sm mb-8">
          <LoginStatus session={session} onSessionUpdated={setSession} />

          {!currentJob && (
            <UrlInput onSubmit={handleSubmit} disabled={isProcessing} />
          )}

          {currentJob && currentJob.status !== 'ready' && currentJob.status !== 'error' && (
            <ProgressCard job={currentJob} />
          )}

          {currentJob && currentJob.status === 'ready' && (
            <ResultCard job={currentJob} onReset={handleReset} onPreview={openPreviewCurrent} />
          )}

          {error && <ErrorCard error={error} onRetry={handleReset} />}

          <HistoryDrawer
            items={history}
            onSelectItem={openPreviewHistory}
            onRemoveItem={(id) => setHistory((p) => p.filter((i) => i.id !== id))}
            onClearHistory={() => setHistory([])}
            isOpen={isHistoryOpen}
            onToggle={() => setIsHistoryOpen(!isHistoryOpen)}
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center text-xs text-muted py-8 border-t border-border">
        <p>Academic PDF Helper · Open Source · Sin almacenamiento de credenciales</p>
        <p className="mt-1 text-[11px] opacity-60">
          FastAPI · React · Playwright · PyMuPDF
        </p>
      </footer>

      {/* Modals */}
      <ArchitectureModal isOpen={isArchOpen} onClose={() => setIsArchOpen(false)} />
      <PdfViewerModal
        isOpen={previewModal.isOpen}
        onClose={() => setPreviewModal((p) => ({ ...p, isOpen: false }))}
        title={previewModal.title}
        previewUrl={previewModal.previewUrl}
        downloadUrl={previewModal.downloadUrl}
        filename={previewModal.filename}
        pages={previewModal.pages}
      />
    </div>
  );
}

export default App;
