/**
 * Search Page
 */
import React, { useState } from 'react';
import { casesAPI } from '../services/api';
import { FiSearch, FiLoader, FiAlertCircle } from 'react-icons/fi';
import CasesList from '../components/CasesList';
import toast from 'react-hot-toast';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (event) => {
    event.preventDefault();

    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setLoading(true);
    try {
      const response = await casesAPI.list({ search: query });
      setResults(response.data.results || response.data);
      setSearched(true);
    } catch (error) {
      console.error('Error searching:', error);
      toast.error('Error performing search');
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Advanced Search</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
          Search cases by case number, party names, judge name, or keywords from the case record.
        </p>

        <form onSubmit={handleSearch} className="mt-5">
          <div className="flex flex-col gap-3 md:flex-row">
            <label className="relative flex-1">
              <span className="sr-only">Search cases</span>
              <FiSearch className="pointer-events-none absolute left-3 top-3.5 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by case number, party name, judge name..."
                className="w-full rounded-md border border-slate-300 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-blue-600 px-5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
            >
              {loading ? <FiLoader className="animate-spin" /> : <FiSearch />}
              {loading ? 'Searching' : 'Search'}
            </button>
          </div>
        </form>
      </header>

      {searched && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {loading ? (
            <div className="flex min-h-[240px] items-center justify-center gap-2 text-slate-500 dark:text-slate-400">
              <FiLoader className="animate-spin" />
              Looking up matching cases...
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-4">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Found {results.length} result{results.length !== 1 ? 's' : ''}
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">Results are sorted by the backend default ordering.</p>
              </div>
              <CasesList cases={results} />
            </div>
          ) : (
            <div className="flex min-h-[240px] items-center justify-center text-center">
              <div className="max-w-md">
                <FiAlertCircle className="mx-auto text-2xl text-slate-400 dark:text-slate-500" />
                <p className="mt-3 text-base font-medium text-slate-900 dark:text-slate-100">
                  No cases matched your search.
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                  Try a case number, a different party name, or a broader keyword.
                </p>
              </div>
            </div>
          )}
        </section>
      )}

      {!searched && (
        <section className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900/60">
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100">Start with a case number or party name.</p>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            Search results will appear here with readable status, party, and hearing details.
          </p>
        </section>
      )}
    </div>
  );
}
