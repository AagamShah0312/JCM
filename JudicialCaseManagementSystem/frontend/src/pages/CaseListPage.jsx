import React, { useCallback, useEffect, useState } from 'react';
import { authAPI, casesAPI, documentsAPI } from '../services/api';
import { useAuthStore } from '../context/authStore';
import CasesList from '../components/CasesList';
import { FiSearch, FiPlus, FiX, FiLoader } from 'react-icons/fi';
import toast from 'react-hot-toast';

const initialCaseForm = {
  case_number: '',
  title: '',
  description: '',
  court_name: '',
  case_type: '',
  filing_date: '',
  next_hearing_date: '',
  status: 'pending',
  judge_name: '',
  assigned_judge: '',
  assigned_lawyer: '',
  public_interest_link: '',
  plaintiff_name: '',
  defendant_name: '',
  documents: [],
};

const formFields = [
  { key: 'case_number', label: 'Case Number', required: true },
  { key: 'title', label: 'Title', required: true },
  { key: 'court_name', label: 'Court Name', required: true },
  { key: 'case_type', label: 'Case Type', required: true },
  { key: 'judge_name', label: 'Judge Name' },
  { key: 'public_interest_link', label: 'Public Interest Live Link' },
  { key: 'plaintiff_name', label: 'Plaintiff Name', required: true },
  { key: 'defendant_name', label: 'Defendant Name', required: true },
];

export default function CaseListPage() {
  const { user } = useAuthStore();
  const canCreateCase = ['admin', 'judge'].includes(user?.role);
  const [cases, setCases] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [savingCase, setSavingCase] = useState(false);
  const [caseForm, setCaseForm] = useState(initialCaseForm);
  const [filters, setFilters] = useState({ status: '', search: '' });
  const today = new Date().toISOString().split('T')[0];

  const fetchCases = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        search: filters.search,
        ...(filters.status && { status: filters.status }),
      };
      const response = await casesAPI.list(params);
      setCases(response.data.results || response.data);
    } catch (error) {
      toast.error('Error loading cases');
    } finally {
      setLoading(false);
    }
  }, [filters.search, filters.status]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  useEffect(() => {
    const fetchStaff = async () => {
      try {
        const response = await authAPI.listUsers();
        setStaff(response.data.results || response.data || []);
      } catch (error) {
        setStaff([]);
      }
    };
    fetchStaff();
  }, []);

  const handleCreateCase = async (event) => {
    event.preventDefault();
    setSavingCase(true);

    try {
      const casePayload = { ...caseForm };
      delete casePayload.document_type;
      delete casePayload.documents;
      if (!casePayload.assigned_judge) delete casePayload.assigned_judge;
      if (!casePayload.assigned_lawyer) delete casePayload.assigned_lawyer;
      const created = await casesAPI.create(casePayload);

      const uploadableDocs = caseForm.documents.filter((item) => item.file);
      if (uploadableDocs.length && created?.data?.id) {
        try {
          await documentsAPI.upload(created.data.id, {
            files: uploadableDocs,
          });
        } catch (uploadError) {
          toast.error('Case created, but file upload failed. You can upload from case details.');
        }
      }

      toast.success('Case created successfully');
      setShowCreateModal(false);
      setCaseForm(initialCaseForm);
      fetchCases();
    } catch (error) {
      const responseData = error?.response?.data;
      let message = responseData?.error || 'Failed to create case';

      if (responseData && typeof responseData === 'object' && !responseData.error) {
        const firstKey = Object.keys(responseData)[0];
        const value = responseData[firstKey];
        message = `${firstKey}: ${Array.isArray(value) ? value[0] : value}`;
      }

      toast.error(message);
    } finally {
      setSavingCase(false);
    }
  };

  const toggleBookmark = async (caseItem) => {
    try {
      if (caseItem.is_bookmarked) {
        await casesAPI.unbookmark(caseItem.id);
        toast.success('Removed from bookmarks');
      } else {
        await casesAPI.bookmark(caseItem.id);
        toast.success('Bookmarked successfully');
      }
      fetchCases();
    } catch (error) {
      toast.error('Bookmark action failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Cases</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
            {canCreateCase ? 'Manage and view court cases.' : 'Browse cases, hearings, and documents.'}
          </p>
        </div>

        {canCreateCase ? (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            <FiPlus size={18} />
            New Case
          </button>
        ) : (
          <span className="text-sm text-slate-500 dark:text-slate-400">Guests and lawyers can view cases only.</span>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="relative flex-1">
            <FiSearch className="pointer-events-none absolute left-3 top-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by case number, party name..."
              value={filters.search}
              onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
              className="w-full rounded-md border border-slate-300 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </div>

          <select
            value={filters.status}
            onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
            className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="active">Active</option>
            <option value="closed">Closed</option>
            <option value="appealed">Appealed</option>
            <option value="postponed">Postponed</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex min-h-[24rem] items-center justify-center gap-2 text-slate-500 dark:text-slate-400">
          <FiLoader className="animate-spin" />
          Loading cases...
        </div>
      ) : cases.length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <CasesList
            cases={cases}
            renderAction={
              user?.role === 'lawyer'
                ? (caseItem) => (
                    <button
                      onClick={() => toggleBookmark(caseItem)}
                      className="rounded-md border border-blue-200 px-3 py-1.5 text-sm font-medium text-blue-700 transition hover:bg-blue-50 dark:border-blue-900/60 dark:text-blue-300 dark:hover:bg-blue-950/40"
                    >
                      {caseItem.is_bookmarked ? 'Remove Bookmark' : 'Bookmark'}
                    </button>
                  )
                : null
            }
          />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100">No cases found.</p>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            Adjust your filters or search terms to find a matching case.
          </p>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 px-4 py-8">
          <div className="mx-auto w-full max-w-5xl">
            <div className="rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Create New Case</h2>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Enter the case record and optionally upload the first document in the same flow.
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                  aria-label="Close"
                >
                  <FiX size={18} />
                </button>
              </div>

              <form onSubmit={handleCreateCase} className="space-y-6 px-6 py-6">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {formFields.map((field) => (
                    <label key={field.key} className="space-y-1">
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        {field.label}
                        {field.required ? ' *' : ''}
                      </span>
                      <input
                        required={field.required}
                        value={caseForm[field.key]}
                        onChange={(event) => setCaseForm((prev) => ({ ...prev, [field.key]: event.target.value }))}
                        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                      />
                    </label>
                  ))}

                  <label className="space-y-1">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Filing Date *</span>
                    <input
                      required
                      type="date"
                      value={caseForm.filing_date}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, filing_date: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Next Hearing Date</span>
                    <input
                      type="date"
                      min={today}
                      value={caseForm.next_hearing_date}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, next_hearing_date: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    />
                  </label>

                  <label className="space-y-1">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Status</span>
                    <select
                      value={caseForm.status}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, status: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    >
                      <option value="pending">Pending</option>
                      <option value="active">Active</option>
                      <option value="closed">Closed</option>
                      <option value="appealed">Appealed</option>
                      <option value="postponed">Postponed</option>
                    </select>
                  </label>

                  <label className="space-y-1 md:col-span-2">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Description *</span>
                    <textarea
                      required
                      rows={5}
                      value={caseForm.description}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, description: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    />
                  </label>

                  <label className="space-y-1 md:col-span-2">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Judge ID</span>
                    <select
                      value={caseForm.assigned_judge}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, assigned_judge: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    >
                      <option value="">Select judge by ID</option>
                      {staff.filter((item) => item.role === 'judge').map((item) => (
                        <option key={item.id} value={item.id}>{item.professional_id || item.id} - {item.first_name || item.email}</option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-1 md:col-span-2">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Lawyer ID</span>
                    <select
                      value={caseForm.assigned_lawyer}
                      onChange={(event) => setCaseForm((prev) => ({ ...prev, assigned_lawyer: event.target.value }))}
                      className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100"
                    >
                      <option value="">Select lawyer by ID</option>
                      {staff.filter((item) => item.role === 'lawyer').map((item) => (
                        <option key={item.id} value={item.id}>{item.professional_id || item.id} - {item.first_name || item.email}</option>
                      ))}
                    </select>
                  </label>

                  <div className="space-y-3 md:col-span-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Initial Documents</span>
                      <button type="button" onClick={() => setCaseForm((prev) => ({ ...prev, documents: [...prev.documents, { file: null, document_type: 'other', description: '' }] }))} className="rounded-md border border-blue-200 px-3 py-1.5 text-sm font-medium text-blue-700 dark:border-blue-900/60 dark:text-blue-300">
                        Add Document
                      </button>
                    </div>
                    {caseForm.documents.map((doc, index) => (
                      <div key={index} className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700 md:grid-cols-3">
                        <input type="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png" onChange={(event) => setCaseForm((prev) => ({ ...prev, documents: prev.documents.map((item, itemIndex) => itemIndex === index ? { ...item, file: event.target.files?.[0] || null } : item) }))} className="rounded-md border border-dashed border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300" />
                        <select value={doc.document_type} onChange={(event) => setCaseForm((prev) => ({ ...prev, documents: prev.documents.map((item, itemIndex) => itemIndex === index ? { ...item, document_type: event.target.value } : item) }))} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100">
                          <option value="statement">Statement</option>
                          <option value="bonafide">Bonafide Document</option>
                          <option value="petition">Petition</option>
                          <option value="affidavit">Affidavit</option>
                          <option value="judgment">Judgment</option>
                          <option value="order">Order</option>
                          <option value="evidence">Evidence</option>
                          <option value="other">Other</option>
                        </select>
                        <input placeholder="Description" value={doc.description} onChange={(event) => setCaseForm((prev) => ({ ...prev, documents: prev.documents.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.target.value } : item) }))} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100" />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingCase}
                    className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
                  >
                    {savingCase ? 'Creating...' : 'Create Case'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
