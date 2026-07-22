/**
 * AI Assistant Page
 */
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { casesAPI } from '../services/api';
import { FiArrowLeft, FiCpu } from 'react-icons/fi';
import toast from 'react-hot-toast';
import CaseAIChatPanel from '../components/CaseAIChatPanel';

export default function AIAssistantPage() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(Boolean(caseId));

  useEffect(() => {
    if (!caseId) {
      setLoading(false);
      return;
    }

    const loadCase = async () => {
      try {
        const response = await casesAPI.retrieve(caseId);
        setCaseData(response.data);
      } catch (error) {
        console.error('Error fetching case:', error);
        toast.error('Error loading AI assistant');
      } finally {
        setLoading(false);
      }
    };

    loadCase();
  }, [caseId]);

  if (!caseId) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            <FiCpu />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">AI Assistant</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">
              Open a case to use the case-aware assistant.
            </p>
            <Link
              to="/cases"
              className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-blue-700 transition hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
            >
              <FiArrowLeft />
              Go to cases
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[24rem] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-500" />
          <p className="mt-4 text-slate-600 dark:text-slate-300">Loading AI Assistant...</p>
        </div>
      </div>
    );
  }

  return <CaseAIChatPanel caseId={caseId} caseData={caseData} />;
}
