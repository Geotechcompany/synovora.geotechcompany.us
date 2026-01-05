import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserButton, useAuth, useUser } from '@clerk/clerk-react';
import { RefreshCw, PlugZap, ShieldCheck } from 'lucide-react';

import { fetchLinkedInStatus, getOpenAiKeyStatus, openLinkedInConnect, setOpenAiKey } from '../lib/api';
import { Skeleton } from '../components/skeleton';
import type { LinkedInStatus, OpenAiKeyStatus } from '../types';

const SettingsPage = () => {
  const navigate = useNavigate();
  const { user } = useUser();
  const { getToken } = useAuth();
  const [status, setStatus] = useState<LinkedInStatus | null>(null);
  const [isStatusLoading, setIsStatusLoading] = useState(false);
  const [openAiStatus, setOpenAiStatus] = useState<OpenAiKeyStatus | null>(null);
  const [isOpenAiStatusLoading, setIsOpenAiStatusLoading] = useState(false);
  const [openAiKeyDraft, setOpenAiKeyDraft] = useState('');
  const [isSavingOpenAiKey, setIsSavingOpenAiKey] = useState(false);
  const [openAiSaveMessage, setOpenAiSaveMessage] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      setIsStatusLoading(true);
      const response = await fetchLinkedInStatus({ clerkUserId: user?.id });
      setStatus(response);
    } catch (error) {
      console.error(error);
    } finally {
      setIsStatusLoading(false);
    }
  };

  const loadOpenAiStatus = async () => {
    try {
      setIsOpenAiStatusLoading(true);
      setOpenAiSaveMessage(null);
      const token = await getToken().catch(() => null);
      if (!token) {
        setOpenAiStatus(null);
        return;
      }
      const response = await getOpenAiKeyStatus({ authToken: token });
      setOpenAiStatus(response);
    } catch (error) {
      console.error(error);
      setOpenAiSaveMessage((error as Error).message);
    } finally {
      setIsOpenAiStatusLoading(false);
    }
  };

  const handleSaveOpenAiKey = async () => {
    const trimmed = openAiKeyDraft.trim();
    if (!trimmed) return;
    try {
      setIsSavingOpenAiKey(true);
      setOpenAiSaveMessage(null);
      const token = await getToken().catch(() => null);
      if (!token) {
        throw new Error('Not authenticated.');
      }
      await setOpenAiKey({ authToken: token, openaiApiKey: trimmed });
      setOpenAiKeyDraft('');
      setOpenAiSaveMessage('Saved.');
      await loadOpenAiStatus();
    } catch (error) {
      setOpenAiSaveMessage((error as Error).message);
    } finally {
      setIsSavingOpenAiKey(false);
    }
  };

  useEffect(() => {
    loadStatus();
    loadOpenAiStatus();
  }, [user?.id]);

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="text-sm font-semibold text-slate-600 hover:text-slate-900"
            >
              ← Back
            </button>
            <h1 className="text-lg font-bold text-slate-900">LinkedIn Settings</h1>
          </div>
          <UserButton />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8">
        <section className="bg-white/90 backdrop-blur rounded-3xl border border-slate-100 p-8 shadow">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-slate-400">
                Connection Status
              </p>
              <h2 className="text-2xl font-semibold text-slate-900">LinkedIn OAuth</h2>
            </div>
          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <p className="text-sm text-slate-500 mb-1">Status</p>
              {isStatusLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-5 w-28" />
                  <Skeleton className="h-4 w-44" />
                </div>
              ) : (
                <p
                  className={`text-lg font-semibold ${
                    status?.authenticated ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {status?.authenticated ? 'Connected' : 'Not Connected'}
                </p>
              )}
              {status?.profile && (
                <p className="text-sm text-slate-500">
                  {status.profile.localizedFirstName} {status.profile.localizedLastName}
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={loadStatus}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold hover:bg-slate-50"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh Status
              </button>
              <button
                type="button"
                onClick={() => openLinkedInConnect({ clerkUserId: user?.id })}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800"
              >
                <PlugZap className="h-4 w-4" />
                Connect LinkedIn
              </button>
            </div>
          </div>

          {status?.message && (
            <p className="mt-4 text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-xl p-4">
              {status.message}
            </p>
          )}
        </section>

        <section className="bg-white/90 backdrop-blur rounded-3xl border border-slate-100 p-8 shadow">
          <div className="flex items-center justify-between gap-6">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-slate-400">AI Fallback</p>
              <h2 className="text-2xl font-semibold text-slate-900">OpenAI API Key</h2>
              <p className="mt-2 text-sm text-slate-500">
                If Gemini/NVIDIA is unavailable, Synvora can use your OpenAI key to generate posts. Your key is stored
                encrypted in the database.
              </p>
            </div>
            <button
              type="button"
              onClick={loadOpenAiStatus}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>

          <div className="mt-6 grid gap-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-slate-500 mb-1">Status</p>
                {isOpenAiStatusLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-5 w-28" />
                    <Skeleton className="h-4 w-44" />
                  </div>
                ) : (
                  <p className={`text-lg font-semibold ${openAiStatus?.has_key ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {openAiStatus?.has_key ? 'Key Saved' : 'No Key Saved'}
                  </p>
                )}
                {openAiStatus?.has_key && openAiStatus.last4 && (
                  <p className="text-sm text-slate-500">Last 4: •••• {openAiStatus.last4}</p>
                )}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-slate-700">OpenAI API Key</span>
                <input
                  type="password"
                  value={openAiKeyDraft}
                  onChange={(e) => setOpenAiKeyDraft(e.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-slate-900/10"
                />
              </label>
              <button
                type="button"
                onClick={handleSaveOpenAiKey}
                disabled={isSavingOpenAiKey || !openAiKeyDraft.trim()}
                className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSavingOpenAiKey ? 'Saving...' : 'Save Key'}
              </button>
            </div>

            {openAiSaveMessage && (
              <p className="text-sm text-slate-500 bg-slate-50 border border-slate-100 rounded-xl p-4">
                {openAiSaveMessage}
              </p>
            )}
          </div>
        </section>

        <section className="bg-white/90 backdrop-blur rounded-3xl border border-slate-100 p-8 shadow">
          <h3 className="text-xl font-semibold text-slate-900 mb-3">How it works</h3>
          <p className="text-sm text-slate-500 mb-6">
            We use OAuth 2.0 with OpenID Connect scopes to publish content on your behalf. CrewAI
            agents create the copy, and the FastAPI backend handles secure publishing.
          </p>
          <ul className="space-y-3 text-sm text-slate-600 list-disc pl-6">
            <li>Use the Connect button to open LinkedIn and authorize access.</li>
            <li>Tokens are stored securely in the backend&apos;s `.env` file.</li>
            <li>You can revoke access from LinkedIn at any time.</li>
          </ul>
        </section>
      </main>
    </div>
  );
};

export default SettingsPage;

