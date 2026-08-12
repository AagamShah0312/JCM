import React, { useEffect, useMemo, useRef, useState } from 'react';
import { aiAPI } from '../services/api';
import { FiMessageSquare, FiSend, FiLoader, FiAlertCircle } from 'react-icons/fi';

export default function CaseAIChatPanel({ caseId, caseData }) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  const title = useMemo(() => {
    if (!caseData) return 'Case chat';
    return `${caseData.case_number} - ${caseData.title}`;
  }, [caseData]);

  useEffect(() => {
    if (!caseId) {
      setLoading(false);
      return;
    }

    const loadConversation = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await aiAPI.getCaseChat(caseId);
        setConversation(response.data.conversation || null);
        setMessages(response.data.messages || []);
      } catch (err) {
        const message = err?.response?.data?.detail || err?.response?.data?.error || 'Unable to load the case chat.';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    loadConversation();
  }, [caseId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (event) => {
    event.preventDefault();
    if (!input.trim() || !caseId) return;

    setSending(true);
    setError('');

    try {
      const response = await aiAPI.sendCaseMessage(caseId, input.trim());
      setConversation(response.data.conversation || conversation);
      setMessages(response.data.messages || []);
      setInput('');
    } catch (err) {
      const message = err?.response?.data?.detail || err?.response?.data?.error || 'Unable to send the message.';
      setError(message);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="flex min-h-[640px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            <FiMessageSquare />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-lg font-semibold text-slate-900 dark:text-slate-100">
              Case AI Chat
            </h3>
            <p className="truncate text-sm text-slate-500 dark:text-slate-400">{title}</p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto bg-slate-50 px-4 py-4 dark:bg-slate-950/30">
        {loading ? (
          <div className="flex h-full min-h-[360px] items-center justify-center gap-2 text-slate-500 dark:text-slate-400">
            <FiLoader className="animate-spin" />
            Loading conversation...
          </div>
        ) : error ? (
          <div className="flex h-full min-h-[360px] items-start justify-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
            <FiAlertCircle className="mt-0.5 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full min-h-[360px] items-center justify-center px-6 text-center">
            <div className="max-w-md">
              <p className="text-base font-medium text-slate-900 dark:text-slate-100">
                Ask a question about this case.
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                The assistant uses the case record, attached documents, and prior conversation history.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm sm:max-w-[78%] ${
                      isUser
                        ? 'bg-blue-600 text-white'
                        : 'border border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="border-t border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <textarea
            rows={3}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about the case, documents, next hearing, or status..."
            className="min-h-[88px] flex-1 resize-none rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-100 dark:placeholder:text-slate-500"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
          >
            {sending ? <FiLoader className="animate-spin" /> : <FiSend />}
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
