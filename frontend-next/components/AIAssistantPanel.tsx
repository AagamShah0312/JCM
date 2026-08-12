'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Bot, Send, AlertTriangle, FileText } from 'lucide-react';
import { aiApi } from '@/lib/services';
import type { AIResponse, Citation } from '@/types';
import { getErrorMessage } from '@/lib/api';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  warnings?: string[];
}

export default function AIAssistantPanel({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');

  const chatMutation = useMutation({
    mutationFn: (content: string) => aiApi.chat(caseId, content),
    onSuccess: (res) => {
      const data = res.data as AIResponse;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer || data.summary || 'No response', citations: data.citations || [], warnings: data.warnings || [] },
      ]);
    },
  });

  const explainMutation = useMutation({
    mutationFn: () => aiApi.explain(caseId),
    onSuccess: (res) => {
      const data = res.data as AIResponse;
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.explanation || data.summary || 'No explanation available',
        citations: data.citations || [],
        warnings: data.warnings || [],
      }]);
    },
  });

  const docsSummaryMutation = useMutation({
    mutationFn: () => aiApi.documentsSummary(caseId),
    onSuccess: (res) => {
      const data = res.data as AIResponse;
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.summary || 'No document summary available',
        citations: data.citations || [],
        warnings: data.warnings || [],
      }]);
    },
  });

  const pushAssistant = (content: string, citations: Citation[] = [], warnings: string[] = []) => {
    setMessages((prev) => [...prev, { role: 'assistant', content, citations, warnings }]);
  };

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: input.trim() }]);
    chatMutation.mutate(input.trim());
    setInput('');
  };

  const openCitation = (c: Citation) => {
    // Citations map to document chunks/hearings within this case.
    // For now, highlight in chat; deep-linking added with the docs tab.
    const el = document.getElementById('case-documents-tab');
    if (c.source_type === 'chunk' || c.source_type === 'document') el?.click();
  };

  return (
    <div className="flex h-[640px] flex-col rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-50 text-brand-600"><Bot size={18} /></div>
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Case AI Assistant</h3>
          <p className="text-xs text-slate-400">Answers based on authorized case documents · advisory only</p>
        </div>
        <button className="btn-secondary ml-auto" onClick={() => explainMutation.mutate()} disabled={explainMutation.isPending}>
          {explainMutation.isPending ? '…' : 'Explain case'}
        </button>
        <button className="btn-secondary" onClick={() => docsSummaryMutation.mutate()} disabled={docsSummaryMutation.isPending}>
          <FileText size={14} /> {docsSummaryMutation.isPending ? '…' : 'Docs summary'}
        </button>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Bot size={40} className="text-slate-300" />
            <p className="mt-3 max-w-sm text-sm text-slate-500">
              Ask about this case — e.g. <em>"What happened in the last hearing?"</em> or <em>"Summarize the witness statement."</em>
            </p>
            <div className="mt-4 flex gap-2">
              {['What happened in the latest hearing?', 'Summarize the case', 'List key documents'].map((q) => (
                <button key={q} className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
                  onClick={() => { setMessages((p) => [...p, { role: 'user', content: q }]); chatMutation.mutate(q); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${m.role === 'user' ? 'bg-brand-600 text-white' : 'border border-slate-200 bg-slate-50 text-slate-800'}`}>
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.warnings && m.warnings.length > 0 && (
                <div className="mt-2 flex items-start gap-1 rounded bg-amber-50 p-1.5 text-[11px] text-amber-700">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {m.warnings[0]}
                </div>
              )}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 border-t border-slate-200 pt-2">
                  <p className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase text-slate-400">
                    <FileText size={11} /> Sources
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {m.citations.slice(0, 6).map((c, ci) => (
                      <button key={ci}
                        className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:border-brand-400 hover:text-brand-600"
                        onClick={() => openCitation(c)} title={c.excerpt || c.source_label}>
                        {c.source_label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-400">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" /> Thinking…
            </div>
          </div>
        )}
      </div>

      <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3">
        <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about this case…" />
        <button className="btn-primary" disabled={chatMutation.isPending || !input.trim()}><Send size={16} /></button>
      </form>
    </div>
  );
}
