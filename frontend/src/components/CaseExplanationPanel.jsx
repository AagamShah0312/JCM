import React, { useEffect, useState } from 'react';
import { aiAPI } from '../services/api';
import { FiAlertCircle, FiClock, FiFileText, FiLoader } from 'react-icons/fi';

export default function CaseExplanationPanel({ caseId, caseData, refreshToken = 0 }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [cached, setCached] = useState(false);
  const [generatedAt, setGeneratedAt] = useState('');

  useEffect(() => {
    if (!caseId) {
      setExplanation(null);
      setError('');
      return;
    }

    const loadExplanation = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await aiAPI.explainCase(caseId);
        setExplanation(response.data.explanation || '');
        setCached(Boolean(response.data.cached));
        setGeneratedAt(response.data.generated_at || '');
      } catch (err) {
        const message = err?.response?.data?.error || 'Unable to explain this case right now.';
        setError(message);
        setExplanation(null);
      } finally {
        setLoading(false);
      }
    };

    loadExplanation();
  }, [caseId, refreshToken]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300">
            <FiFileText />
            Explain Case
          </div>
          <h3 className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
            Simplified case explanation
          </h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {caseData?.case_number ? `${caseData.case_number} - ${caseData.title}` : 'A concise explanation will appear here.'}
          </p>
        </div>

        {generatedAt ? (
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <FiClock />
            {cached ? 'Loaded from cache' : 'Generated fresh'} | {new Date(generatedAt).toLocaleString()}
          </div>
        ) : null}
      </div>

      <div className="mt-4 min-h-[140px] rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
        {loading ? (
          <div className="flex h-full items-center justify-center gap-2 py-8 text-slate-500 dark:text-slate-400">
            <FiLoader className="animate-spin" />
            Generating explanation...
          </div>
        ) : error ? (
          <div className="flex items-start gap-3 text-red-700 dark:text-red-300">
            <FiAlertCircle className="mt-0.5 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        ) : explanation ? (
          <div className="space-y-3 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-200">
            {explanation}
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No explanation available yet.
          </p>
        )}
      </div>
    </section>
  );
}
