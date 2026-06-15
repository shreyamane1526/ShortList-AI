// LinkedInHackathon/frontend/src/components/inclusion/AccessibleSummaryModal.tsx
import { useState, useEffect } from 'react';
import { FileText, Copy, Check, RefreshCw, X } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { generateAccessibleSummary } from '@/services/inclusionApi';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

interface AccessibleSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  evaluationId: number;
  format?: 'standard' | 'adhd_friendly' | 'dyslexia_friendly';
}

export function AccessibleSummaryModal({
  isOpen,
  onClose,
  evaluationId,
  format = 'adhd_friendly',
}: AccessibleSummaryModalProps) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [currentFormat, setCurrentFormat] = useState(format);

  const fetchSummary = async (fmt: typeof currentFormat) => {
    setLoading(true);
    try {
      const result = await generateAccessibleSummary(evaluationId, fmt);
      setSummary(result.summary);
    } catch (error) {
      toast.error('Failed to load accessible summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && evaluationId) {
      fetchSummary(currentFormat);
    }
  }, [isOpen, evaluationId, currentFormat]);

  const handleCopy = async () => {
    if (!summary) return;
    await navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success('Copied to clipboard');
  };

  const handleFormatChange = (newFormat: typeof currentFormat) => {
    setCurrentFormat(newFormat);
  };

  return (
    <Modal open={isOpen} onClose={onClose} title="Accessible Evaluation Summary" size="lg">
      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-purple-600" />
            <span className="text-sm text-gray-500">
              Plain‑language summary, optimised for readability
            </span>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={currentFormat}
              onChange={(e) => handleFormatChange(e.target.value as any)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:ring-purple-500"
            >
              <option value="standard">Standard</option>
              <option value="adhd_friendly">ADHD‑friendly (concise)</option>
              <option value="dyslexia_friendly">Dyslexia‑friendly (clear fonts)</option>
            </select>
            <button
              onClick={() => fetchSummary(currentFormat)}
              disabled={loading}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={cn('w-4 h-4 text-gray-500', loading && 'animate-spin')} />
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-xl p-5 min-h-[200px] max-h-[400px] overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : summary ? (
            <div className="prose prose-sm max-w-none">
              {currentFormat === 'adhd_friendly' ? (
                // Render bullet points for ADHD-friendly
                <div className="space-y-2">
                  {summary.split('\n').map((line, idx) => {
                    if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
                      return <div key={idx} className="flex items-start gap-2 text-gray-700"><span className="text-purple-500">•</span><span>{line.replace(/^[-•]\s*/, '')}</span></div>;
                    }
                    return <p key={idx} className="text-gray-700">{line}</p>;
                  })}
                </div>
              ) : currentFormat === 'dyslexia_friendly' ? (
                <div className="space-y-3 text-gray-800" style={{ fontFamily: 'OpenDyslexic, Arial, sans-serif', lineHeight: 1.6 }}>
                  {summary.split('\n').map((line, idx) => (
                    <p key={idx}>{line}</p>
                  ))}
                </div>
              ) : (
                <div className="whitespace-pre-wrap text-gray-700">
                  {summary}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-12">
              No summary available
            </div>
          )}
        </div>

        <div className="flex gap-3 pt-2">
          <button onClick={handleCopy} disabled={!summary} className="btn-secondary flex-1 justify-center">
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy to clipboard'}
          </button>
          <button onClick={onClose} className="btn-primary flex-1 justify-center">
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}