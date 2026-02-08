import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserButton, useAuth } from '@clerk/clerk-react';
import { Zap, RefreshCw, Save } from 'lucide-react';
import clsx from 'clsx';

import { getAutomationSetting, setAutomationSetting, getAutomationLogs } from '../lib/api';
import { Skeleton } from '../components/skeleton';
import { useModal } from '../components/modal-context';
import type { AutomationSetting as AutomationSettingType, AutomationLogEntry } from '../types';

const AutomationsPage = () => {
  const navigate = useNavigate();
  const { getToken, isLoaded } = useAuth();
  const { showToast } = useModal();
  const [setting, setSetting] = useState<AutomationSettingType | null>(null);
  const [occupationDraft, setOccupationDraft] = useState('');
  const [frequencyDraft, setFrequencyDraft] = useState<'daily' | 'weekly'>('daily');
  const [logs, setLogs] = useState<AutomationLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [logsLoading, setLogsLoading] = useState(true);

  const loadSetting = async () => {
    try {
      const token = await getToken().catch(() => null);
      const t = typeof token === 'string' ? token.trim() : '';
      if (!t) return;
      const data = await getAutomationSetting({ authToken: t });
      setSetting(data);
      setOccupationDraft(data.occupation ?? '');
      setFrequencyDraft((data.frequency as 'daily' | 'weekly') || 'daily');
    } catch (e) {
      showToast((e as Error).message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      setLogsLoading(true);
      const token = await getToken().catch(() => null);
      const t = typeof token === 'string' ? token.trim() : '';
      if (!t) return;
      const data = await getAutomationLogs({ authToken: t }, 20);
      setLogs(data.logs ?? []);
    } catch {
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoaded) return;
    loadSetting();
    loadLogs();
  }, [isLoaded]);

  const handleToggle = async (enabled: boolean) => {
    if (enabled && !(occupationDraft || (setting?.occupation ?? '')).trim()) {
      showToast('Set your profession below before enabling automation.', 'warning');
      return;
    }
    try {
      setIsToggling(true);
      const token = await getToken().catch(() => null);
      if (!token) throw new Error('Not authenticated.');
      const updated = await setAutomationSetting({ enabled }, { authToken: token });
      setSetting(updated);
      showToast(enabled ? 'Automation enabled.' : 'Automation disabled.', 'success');
    } catch (e) {
      showToast((e as Error).message, 'error');
    } finally {
      setIsToggling(false);
    }
  };

  const handleSaveSettings = async () => {
    try {
      setIsSaving(true);
      const token = await getToken().catch(() => null);
      if (!token) throw new Error('Not authenticated.');
      const updated = await setAutomationSetting(
        { occupation: occupationDraft.trim() || undefined, frequency: frequencyDraft },
        { authToken: token },
      );
      setSetting(updated);
      showToast('Settings saved.', 'success');
    } catch (e) {
      showToast((e as Error).message, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const formatRunAt = (runAt: string) => {
    try {
      const d = new Date(runAt);
      return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return runAt;
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900">
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="text-sm font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 shrink-0"
            >
              ← Back
            </button>
            <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100 truncate">Automations</h1>
          </div>
          <UserButton />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        {/* Section 1: Enable/disable */}
        <section className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Auto-create posts from trends</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                When enabled, we create draft posts for you based on trending topics in your profession.
              </p>
            </div>
          </div>
          {isLoading ? (
            <Skeleton className="h-10 w-24 rounded-xl" />
          ) : (
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={setting?.enabled ?? false}
                disabled={isToggling}
                onClick={() => handleToggle(!(setting?.enabled ?? false))}
                className={clsx(
                  'relative inline-flex h-7 w-12 shrink-0 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500/30',
                  (setting?.enabled ?? false)
                    ? 'bg-amber-500 dark:bg-amber-600'
                    : 'bg-slate-200 dark:bg-slate-600',
                  isToggling && 'opacity-70',
                )}
              >
                <span
                  className={clsx(
                    'inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform mt-1',
                    (setting?.enabled ?? false) ? 'translate-x-6 ml-0.5' : 'translate-x-1',
                  )}
                />
              </button>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {(setting?.enabled ?? false) ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          )}
        </section>

        {/* Section 2: Automation settings form */}
        <section className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Automation settings</h2>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full rounded-xl" />
              <Skeleton className="h-10 w-32 rounded-xl" />
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Profession / occupation
                </label>
                <input
                  type="text"
                  value={occupationDraft}
                  onChange={(e) => setOccupationDraft(e.target.value)}
                  placeholder="e.g. Software Engineering, Marketing"
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition"
                />
                {((setting?.enabled ?? false) && !(occupationDraft || (setting?.occupation ?? '')).trim()) && (
                  <p className="mt-1.5 text-sm text-amber-600 dark:text-amber-400">
                    Set your profession above so we can find relevant trends.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Frequency
                </label>
                <select
                  value={frequencyDraft}
                  onChange={(e) => setFrequencyDraft(e.target.value as 'daily' | 'weekly')}
                  className="w-full max-w-xs px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
              <button
                type="button"
                onClick={handleSaveSettings}
                disabled={isSaving}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-700 text-white text-sm font-semibold hover:bg-slate-800 dark:hover:bg-slate-600 transition disabled:opacity-60"
              >
                <Save className="h-4 w-4" />
                {isSaving ? 'Saving…' : 'Save settings'}
              </button>
            </div>
          )}
        </section>

        {/* Section 3: Logs */}
        <section className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Recent runs</h2>
            <button
              type="button"
              onClick={loadLogs}
              disabled={logsLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition disabled:opacity-60"
            >
              <RefreshCw className={clsx('h-4 w-4', logsLoading && 'animate-spin')} />
              Refresh
            </button>
          </div>
          {logsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
            </div>
          ) : logs.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 py-4">
              No runs yet. Enable automation and wait for the next scheduled run, or trigger the cron manually.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-600">
                    <th className="text-left py-2 font-semibold text-slate-700 dark:text-slate-300">Run at</th>
                    <th className="text-left py-2 font-semibold text-slate-700 dark:text-slate-300">Status</th>
                    <th className="text-left py-2 font-semibold text-slate-700 dark:text-slate-300">Posts</th>
                    <th className="text-left py-2 font-semibold text-slate-700 dark:text-slate-300">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((entry, i) => (
                    <tr key={i} className="border-b border-slate-100 dark:border-slate-700/70">
                      <td className="py-3 text-slate-600 dark:text-slate-400">{formatRunAt(entry.run_at)}</td>
                      <td className="py-3">
                        <span
                          className={clsx(
                            'inline-flex px-2 py-0.5 rounded-md text-xs font-medium',
                            entry.status === 'success' &&
                              'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300',
                            entry.status === 'failed' &&
                              'bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300',
                            entry.status === 'partial' &&
                              'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300',
                          )}
                        >
                          {entry.status}
                        </span>
                      </td>
                      <td className="py-3 text-slate-700 dark:text-slate-300">{entry.posts_created}</td>
                      <td className="py-3 text-slate-500 dark:text-slate-400 max-w-[200px] truncate" title={entry.error_message ?? ''}>
                        {entry.error_message ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default AutomationsPage;
