/**
 * Case Detail Page
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { casesAPI, documentsAPI } from '../services/api';
import { FiArrowLeft, FiClock, FiCpu, FiFileText, FiRefreshCw } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { useAuthStore } from '../context/authStore';
import { formatDisplayDate } from '../lib/date';
import CaseExplanationPanel from '../components/CaseExplanationPanel';
import CaseAIChatPanel from '../components/CaseAIChatPanel';

const emptyEditState = {
  title: '',
  description: '',
  court_name: '',
  case_type: '',
  filing_date: '',
  next_hearing_date: '',
  status: 'pending',
  judge_name: '',
  plaintiff_name: '',
  defendant_name: '',
  public_interest_link: '',
};

export default function CaseDetailPage() {
  const { user } = useAuthStore();
  const { id } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('details');
  const [documents, setDocuments] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState(emptyEditState);
  const [hearingDate, setHearingDate] = useState('');
  const [hearingDocs, setHearingDocs] = useState([]);
  const [documentRows, setDocumentRows] = useState([]);
  const [explanationRefreshKey, setExplanationRefreshKey] = useState(0);
  const canEditCase = ['admin', 'judge'].includes(user?.role);

  const fetchCaseDetails = useCallback(async () => {
    try {
      setLoading(true);
      const response = await casesAPI.retrieve(id);
      setCaseData(response.data);
      setEditData({
        title: response.data.title || '',
        description: response.data.description || '',
        court_name: response.data.court_name || '',
        case_type: response.data.case_type || '',
        filing_date: response.data.filing_date || '',
        next_hearing_date: response.data.next_hearing_date || '',
        status: response.data.status || 'pending',
        judge_name: response.data.judge_name || '',
        plaintiff_name: response.data.plaintiff_name || '',
        defendant_name: response.data.defendant_name || '',
        public_interest_link: response.data.public_interest_link || '',
      });
      setHearingDate(response.data.next_hearing_date || '');

      const docsResponse = await documentsAPI.list({ case: id });
      setDocuments(docsResponse.data.results || docsResponse.data || []);
    } catch (error) {
      console.error('Error fetching case:', error);
      toast.error('Error loading case details');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchCaseDetails();
  }, [fetchCaseDetails]);

  const hearingDates = useMemo(() => {
    return Array.from(
      new Set(
        (caseData?.timeline_events || [])
          .filter((event) => event.event_type === 'hearing')
          .map((event) => event.event_date)
      )
    ).sort((a, b) => new Date(a) - new Date(b));
  }, [caseData]);

  const backendBase = (process.env.REACT_APP_API_URL || 'http://localhost:8000/api').replace('/api', '');
  const resolveFileUrl = (path) => {
    if (!path) return '#';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    return `${backendBase}${path}`;
  };

  const today = new Date().toISOString().split('T')[0];

  const handleFinishCase = async () => {
    try {
      await casesAPI.finish(id);
      toast.success('Case marked as finished');
      fetchCaseDetails();
    } catch (error) {
      toast.error(error?.response?.data?.error || 'Failed to finish case');
    }
  };

  const handleSaveCase = async () => {
    try {
      await casesAPI.update(id, editData);
      toast.success('Case updated successfully');
      setEditMode(false);
      fetchCaseDetails();
    } catch (error) {
      const data = error?.response?.data;
      if (data && typeof data === 'object') {
        const key = Object.keys(data)[0];
        const value = data[key];
        toast.error(`${key}: ${Array.isArray(value) ? value[0] : value}`);
      } else {
        toast.error('Failed to update case');
      }
    }
  };

  const handleUpdateHearing = async () => {
    try {
      await casesAPI.updateHearing(id, { next_hearing_date: hearingDate, files: hearingDocs });
      toast.success('Next hearing date updated');
      setHearingDocs([]);
      fetchCaseDetails();
    } catch (error) {
      const data = error?.response?.data;
      if (data && typeof data === 'object') {
        const key = Object.keys(data)[0];
        const value = data[key];
        toast.error(`${key}: ${Array.isArray(value) ? value[0] : value}`);
      } else {
        toast.error('Failed to update next hearing date');
      }
    }
  };

  const handleUploadDocuments = async () => {
    try {
      const files = documentRows.filter((item) => item.file);
      if (!files.length) {
        toast.error('Add at least one file');
        return;
      }
      await documentsAPI.upload(id, { files });
      toast.success('Documents uploaded');
      setDocumentRows([]);
      fetchCaseDetails();
    } catch (error) {
      toast.error('Document upload failed');
    }
  };

  const updateDocRow = (rowsSetter, index, patch) => {
    rowsSetter((prev) => prev.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };

  const addDocRow = (rowsSetter) => {
    rowsSetter((prev) => [...prev, { file: null, document_type: 'statement', description: '' }]);
  };

  const renderDocumentRows = (rows, rowsSetter) => (
    <div className="space-y-3">
      {rows.map((doc, index) => (
        <div key={index} className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700 md:grid-cols-3">
          <input type="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png" onChange={(event) => updateDocRow(rowsSetter, index, { file: event.target.files?.[0] || null })} className="rounded-md border border-dashed border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300" />
          <select value={doc.document_type} onChange={(event) => updateDocRow(rowsSetter, index, { document_type: event.target.value })} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100">
            <option value="statement">Statement</option>
            <option value="bonafide">Bonafide Document</option>
            <option value="petition">Petition</option>
            <option value="affidavit">Affidavit</option>
            <option value="judgment">Judgment</option>
            <option value="order">Order</option>
            <option value="evidence">Evidence</option>
            <option value="other">Other</option>
          </select>
          <input placeholder="Description" value={doc.description} onChange={(event) => updateDocRow(rowsSetter, index, { description: event.target.value })} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100" />
        </div>
      ))}
    </div>
  );

  const openExplanation = () => {
    setActiveTab('ai');
    setExplanationRefreshKey((value) => value + 1);
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-500" />
          <p className="mt-4 text-slate-600 dark:text-slate-300">Loading case details...</p>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <p className="text-slate-600 dark:text-slate-300">Case not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <Link
              to="/cases"
              className="mt-1 inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
              aria-label="Back to cases"
            >
              <FiArrowLeft size={20} />
            </Link>

            <div className="min-w-0">
              <p className="text-sm font-medium text-blue-700 dark:text-blue-300">{caseData.case_number}</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 lg:text-3xl">
                {caseData.title}
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-400">
                {caseData.description}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={openExplanation}
              className="inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/50"
            >
              <FiRefreshCw size={16} />
              Explain Case
            </button>

            {user?.role === 'admin' && caseData.status !== 'closed' && (
              <button
                onClick={handleFinishCase}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700"
              >
                Finish Case
              </button>
            )}

            {canEditCase && (
              <button
                onClick={() => setEditMode((value) => !value)}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                {editMode ? 'Cancel Edit' : 'Edit Case'}
              </button>
            )}
          </div>
        </div>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        {editMode ? (
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {[
                ['title', 'Case Title'],
                ['court_name', 'Court Name'],
                ['case_type', 'Case Type'],
                ['judge_name', 'Judge Name'],
                ['public_interest_link', 'Public Interest Live Link'],
                ['plaintiff_name', 'Plaintiff Name'],
                ['defendant_name', 'Defendant Name'],
              ].map(([key, label]) => (
                <label key={key} className="space-y-1">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span>
                  <input
                    value={editData[key]}
                    onChange={(event) => setEditData((prev) => ({ ...prev, [key]: event.target.value }))}
                    className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                  />
                </label>
              ))}

              <label className="space-y-1">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Filing Date</span>
                <input
                  type="date"
                  value={editData.filing_date || ''}
                  onChange={(event) => setEditData((prev) => ({ ...prev, filing_date: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                />
              </label>

              <label className="space-y-1">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Next Hearing Date</span>
                <input
                  type="date"
                  min={today}
                  value={editData.next_hearing_date || ''}
                  onChange={(event) => setEditData((prev) => ({ ...prev, next_hearing_date: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                />
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Status</span>
                <select
                  value={editData.status}
                  onChange={(event) => setEditData((prev) => ({ ...prev, status: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                >
                  <option value="pending">Pending</option>
                  <option value="active">Active</option>
                  <option value="appealed">Appealed</option>
                  <option value="closed">Closed</option>
                  <option value="postponed">Postponed</option>
                </select>
              </label>

              <label className="space-y-1 md:col-span-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Description</span>
                <textarea
                  value={editData.description}
                  onChange={(event) => setEditData((prev) => ({ ...prev, description: event.target.value }))}
                  rows={5}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                />
              </label>
            </div>

            <div className="flex justify-end">
              <button onClick={handleSaveCase} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700">
                Save Changes
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ['Status', caseData.status, true],
              ['Court', caseData.court_name],
              ['Judge', caseData.judge_name || 'N/A'],
              ['Plaintiff', caseData.plaintiff_name],
              ['Defendant', caseData.defendant_name],
              ['Next Hearing', formatDisplayDate(caseData.next_hearing_date)],
            ].map(([label, value, capitalize]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
                <p className={`mt-1 text-base font-semibold text-slate-900 dark:text-slate-100 ${capitalize ? 'capitalize' : ''}`}>
                  {value}
                </p>
              </div>
            ))}
          </div>
        )}

        {caseData.public_interest_link && (
          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/60 dark:bg-blue-950/30">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200">Public Interest Link</p>
            <a href={caseData.public_interest_link} target="_blank" rel="noreferrer" className="mt-1 block break-all text-sm text-blue-700 underline dark:text-blue-300">{caseData.public_interest_link}</a>
          </div>
        )}

        {canEditCase && (
          <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
            <p className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">Update Next Hearing Date</p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                type="date"
                min={today}
                value={hearingDate || ''}
                onChange={(event) => setHearingDate(event.target.value)}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 sm:max-w-xs"
              />
              <button
                onClick={handleUpdateHearing}
                className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                Update Hearing
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Optional Hearing Documents</p>
                <button type="button" onClick={() => addDocRow(setHearingDocs)} className="rounded-md border border-blue-200 px-3 py-1.5 text-sm font-medium text-blue-700 dark:border-blue-900/60 dark:text-blue-300">Add File</button>
              </div>
              {renderDocumentRows(hearingDocs, setHearingDocs)}
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="border-b border-slate-200 dark:border-slate-700">
          <nav className="flex flex-wrap gap-1 px-3 pt-3">
            {[
              { id: 'details', label: 'Documents', icon: FiFileText },
              { id: 'timeline', label: 'Timeline', icon: FiClock },
              { id: 'ai', label: 'AI Assistant', icon: FiCpu },
            ].map(({ id: tabId, label, icon: Icon }) => (
              <button
                key={tabId}
                onClick={() => setActiveTab(tabId)}
                className={`inline-flex items-center gap-2 rounded-t-md border border-b-0 px-4 py-3 text-sm font-medium transition ${
                  activeTab === tabId
                    ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300'
                    : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/60 dark:hover:text-slate-100'
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'details' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Case Description</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {caseData.description}
                </p>
              </div>

              <div>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Uploaded Documents</h3>
                  {canEditCase && (
                    <button type="button" onClick={() => addDocRow(setDocumentRows)} className="rounded-md border border-blue-200 px-3 py-1.5 text-sm font-medium text-blue-700 dark:border-blue-900/60 dark:text-blue-300">Add Document</button>
                  )}
                </div>
                {canEditCase && documentRows.length > 0 && (
                  <div className="mt-4 space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                    {renderDocumentRows(documentRows, setDocumentRows)}
                    <div className="flex justify-end">
                      <button onClick={handleUploadDocuments} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">Upload Documents</button>
                    </div>
                  </div>
                )}
                <div className="mt-4">
                  {documents.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center dark:border-slate-700">
                      <p className="text-sm text-slate-500 dark:text-slate-400">No documents uploaded for this case.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {documents.map((doc) => {
                        const fileUrl = resolveFileUrl(doc.file_url || doc.file);
                        const isImage = /\.(jpg|jpeg|png)$/i.test(doc.file_name || '');
                        const isPdf = /\.pdf$/i.test(doc.file_name || '');

                        return (
                          <article key={doc.id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                              <div>
                                <p className="font-medium text-slate-900 dark:text-slate-100">{doc.file_name}</p>
                                <p className="text-sm text-slate-500 dark:text-slate-400">{doc.document_type}</p>
                              </div>

                              <a
                                href={fileUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
                              >
                                Download
                              </a>
                            </div>

                            <div className="mt-3">
                              {isImage && (
                                <img
                                  src={fileUrl}
                                  alt={doc.file_name}
                                  className="max-h-64 rounded-md border border-slate-200 object-contain dark:border-slate-700"
                                />
                              )}
                              {isPdf && (
                                <iframe
                                  title={doc.file_name}
                                  src={fileUrl}
                                  className="h-80 w-full rounded-md border border-slate-200 dark:border-slate-700"
                                />
                              )}
                              {!isImage && !isPdf && (
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                  Preview not available for this file type.
                                </p>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Hearing Timeline</h3>
              {hearingDates.length > 0 ? (
                <div className="space-y-3">
                  {hearingDates.map((dateValue, index) => (
                    <div
                      key={`${dateValue}-${index}`}
                      className="rounded-lg border border-slate-200 p-4 dark:border-slate-700"
                    >
                      <div className="flex items-center gap-3">
                        <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                          Hearing {index + 1}
                        </span>
                        <p className="text-sm text-slate-600 dark:text-slate-300">{formatDisplayDate(dateValue)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No hearing dates available yet.</p>
              )}
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-6">
              <CaseExplanationPanel
                caseId={id}
                caseData={caseData}
                refreshToken={explanationRefreshKey}
              />
              <CaseAIChatPanel caseId={id} caseData={caseData} />

              <div className="flex justify-end">
                <Link
                  to={`/ai/${id}`}
                  className="inline-flex items-center gap-2 text-sm font-medium text-blue-700 transition hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                >
                  Open full AI assistant
                </Link>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
