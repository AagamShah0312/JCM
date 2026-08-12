'use client';

import { useState } from 'react';
import { Upload, CheckCircle2, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, Badge } from '@/components/ui';
import { csvApi } from '@/lib/services';
import toast from 'react-hot-toast';
import { getErrorMessage } from '@/lib/api';

type ImportType = 'staff' | 'cases';

export default function CSVImportPage() {
  const [type, setType] = useState<ImportType>('staff');
  const [role, setRole] = useState('judge');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [importing, setImporting] = useState(false);

  const runPreview = async () => {
    if (!file) return toast.error('Choose a CSV file first');
    try {
      const res = type === 'staff'
        ? await csvApi.staffPreview(role, file)
        : await csvApi.casesPreview(file);
      setPreview(res.data);
      toast.success(`Preview ready: ${res.data.valid_count} valid, ${res.data.error_count} errors`);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const runImport = async () => {
    if (!preview || !preview.preview?.length) return toast.error('No valid rows to import');
    setImporting(true);
    try {
      const res = type === 'staff'
        ? await csvApi.staffImport(role, preview.preview)
        : await csvApi.casesImport(preview.preview);
      toast.success(`Imported ${res.data.created} record(s)`);
      setPreview({ ...preview, imported: res.data });
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setImporting(false);
    }
  };

  const downloadErrors = async () => {
    if (!file) return toast.error('Choose a CSV file first');
    try {
      const res = await csvApi.errorReport(type, role, file);
      const url = window.URL.createObjectURL(new Blob([res.data as BlobPart]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `csv_import_errors_${type}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Error report downloaded');
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <AppShell>
      <SectionTitle title="CSV Import" subtitle="Validate → preview → confirm → import (no unvalidated data is inserted)" />

      <Card className="mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-md border border-slate-300">
            {(['staff', 'cases'] as ImportType[]).map((t) => (
              <button key={t} className={`px-4 py-2 text-sm font-medium ${type === t ? 'bg-brand-600 text-white' : 'text-slate-600'}`}
                onClick={() => { setType(t); setPreview(null); }}>
                {t === 'staff' ? 'Staff (Judges/Lawyers)' : 'Cases'}
              </button>
            ))}
          </div>
          {type === 'staff' && (
            <select className="input sm:w-40" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="judge">Judges</option>
              <option value="lawyer">Lawyers</option>
            </select>
          )}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <input type="file" accept=".csv" className="text-sm" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="btn-primary" onClick={runPreview}><Upload size={16} /> Preview</button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          {type === 'staff'
            ? 'Expected columns: id/professional_id, email, first_name, last_name (optional: username, password, phone_number)'
            : 'Expected columns: case_number, title, case_type, filing_date, status, plaintiff_name, defendant_name, judge_email, lawyer_email'}
        </p>
      </Card>

      {preview && (
        <Card>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Badge tone="blue">Total rows: {preview.total_rows}</Badge>
            <Badge tone="green"><CheckCircle2 size={12} className="mr-1 inline" /> Valid: {preview.valid_count}</Badge>
            <Badge tone="red"><AlertTriangle size={12} className="mr-1 inline" /> Errors: {preview.error_count}</Badge>
          </div>

          {preview.errors?.length > 0 && (
            <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-semibold text-red-700">Row-level validation errors</p>
                <button className="btn-secondary text-xs" onClick={downloadErrors}>
                  <FileSpreadsheet size={13} className="mr-1 inline" /> Download error report
                </button>
              </div>
              <ul className="max-h-40 space-y-1 overflow-y-auto text-xs text-red-600">
                {preview.errors.slice(0, 50).map((e: any, i: number) => (
                  <li key={i}>Row {e.row} · {e.field}: {e.message}</li>
                ))}
              </ul>
            </div>
          )}

          {preview.preview?.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="table-base">
                  <thead>
                    <tr>{Object.keys(preview.preview[0]).slice(0, 8).map((k) => <th key={k}>{k}</th>)}</tr>
                  </thead>
                  <tbody>
                    {preview.preview.slice(0, 20).map((row: any, i: number) => (
                      <tr key={i}>
                        {Object.values(row).slice(0, 8).map((v: any, j: number) => (
                          <td key={j} className="max-w-[160px] truncate">{v === null || v === '' ? '—' : String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4">
                <button className="btn-primary" disabled={importing} onClick={runImport}>
                  <FileSpreadsheet size={16} /> {importing ? 'Importing…' : `Confirm & Import ${preview.valid_count} row(s)`}
                </button>
                {preview.imported && (
                  <p className="mt-2 text-sm text-emerald-600">Import complete: {preview.imported.created} created, {preview.imported.updated || 0} updated</p>
                )}
              </div>
            </>
          )}
        </Card>
      )}
    </AppShell>
  );
}
