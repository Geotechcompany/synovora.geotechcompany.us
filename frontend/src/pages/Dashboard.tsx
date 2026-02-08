import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserButton, useAuth, useClerk, useUser } from '@clerk/clerk-react';
import {
  LayoutDashboard,
  Sparkles,
  FileText,
  Menu,
  FileEdit,
  CheckCircle2,
  Clock3,
  Plus,
  Pencil,
  Save,
  Send,
  Trash2,
  RefreshCcw,
  Ghost,
  Mail,
} from 'lucide-react';
import clsx from 'clsx';

import { BRAND } from '../config/brand';
import { Skeleton } from '../components/skeleton';
import { ActivityAreaChart } from '../components/charts/activity-area';
import { StatusDonutChart } from '../components/charts/status-donut';
import { ThemeToggle } from '../components/theme-toggle';
import { useModal } from '../components/modal-context';
import {
  deletePost,
  emailPost,
  fetchLinkedInStatus,
  fetchPosts,
  fetchProfileInsights,
  generatePost,
  generateImage,
  openLinkedInConnect,
  publishPost,
  schedulePost,
  suggestTopics,
  updatePost,
} from '../lib/api';
import type { LinkedInStatus, PostRecord, PostStatus, ProfileInsights } from '../types';

type Section = 'dashboard' | 'generate' | 'posts';

const sections: Array<{ id: Section; label: string; icon: React.ElementType }> = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'generate', label: 'Generate', icon: Sparkles },
  { id: 'posts', label: 'Posts', icon: FileText },
];

const DashboardPage = () => {
  const navigate = useNavigate();
  const { signOut } = useClerk();
  const { user } = useUser();
  const { getToken } = useAuth();
  const { showModal, showToast, showInput } = useModal();

  const [activeSection, setActiveSection] = useState<Section>('dashboard');
  const [posts, setPosts] = useState<PostRecord[]>([]);
  const [isPostsLoading, setIsPostsLoading] = useState(false);
  const [filter, setFilter] = useState<PostStatus | null>(null);
  const [linkedinStatus, setLinkedinStatus] = useState<LinkedInStatus | null>(null);
  const [isLinkedInStatusLoading, setIsLinkedInStatusLoading] = useState(false);
  const [profileInsights, setProfileInsights] = useState<ProfileInsights | null>(null);
  const [isInsightsLoading, setIsInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [topic, setTopic] = useState('');
  const [context, setContext] = useState('');
  const [occupation, setOccupation] = useState('');
  const [suggestedTopics, setSuggestedTopics] = useState<string[]>([]);
  const [isSuggestingTopics, setIsSuggestingTopics] = useState(false);
  const [suggestTopicsError, setSuggestTopicsError] = useState<string | null>(null);
  const [currentPost, setCurrentPost] = useState<PostRecord | null>(null);
  const [wordCount, setWordCount] = useState(0);
  const [scheduleFor, setScheduleFor] = useState('');
  const [scheduleVisibility, setScheduleVisibility] = useState<'PUBLIC' | 'CONNECTIONS'>('PUBLIC');

  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [loadingTitle, setLoadingTitle] = useState('Processing');
  const [loadingText, setLoadingText] = useState('Please wait');

  useEffect(() => {
    loadPosts(filter ?? undefined);
    loadProfileInsights();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!user?.id) return;
    refreshLinkedInStatus();
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (filter !== null) {
      loadPosts(filter);
    } else {
      loadPosts();
    }
  }, [filter]);

  useEffect(() => {
    if (currentPost?.image_url) {
      setImagePreview(currentPost.image_url);
      setImageError(null);
      return;
    }
    if (currentPost?.image_base64) {
      const mime = currentPost.image_mime_type || 'image/png';
      setImagePreview(`data:${mime};base64,${currentPost.image_base64}`);
      setImageError(null);
      return;
    }
    if (!currentPost) {
      setImagePreview(null);
    }
  }, [currentPost?.image_url, currentPost?.image_base64, currentPost?.image_mime_type, currentPost]);

  const loadPosts = async (status?: PostStatus | null) => {
    try {
      setIsPostsLoading(true);
      const data = await fetchPosts(status);
      if (data.success) {
        setPosts(data.posts);
      }
    } catch (error) {
      console.error('Failed to load posts', error);
    } finally {
      setIsPostsLoading(false);
    }
  };

  const loadProfileInsights = async () => {
    try {
      setIsInsightsLoading(true);
      const data = await fetchProfileInsights();
      if (data.success) {
        setProfileInsights(data);
        setInsightsError(null);
      } else {
        setInsightsError(data.error || 'Unable to load LinkedIn analytics');
      }
    } catch (error) {
      setInsightsError((error as Error).message);
    } finally {
      setIsInsightsLoading(false);
    }
  };

  const refreshLinkedInStatus = async () => {
    try {
      setIsLinkedInStatusLoading(true);
      const status = await fetchLinkedInStatus({ clerkUserId: user?.id });
      setLinkedinStatus(status);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLinkedInStatusLoading(false);
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return 'Not yet';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleDateString();
  };

  const formatMetric = (value?: number | null) => {
    if (value === null || value === undefined) {
      return '—';
    }
    return value.toLocaleString();
  };

  const stats = useMemo(() => {
    const total = posts.length;
    const published = posts.filter((p) => p.status === 'published').length;
    const drafts = posts.filter((p) => p.status === 'draft').length;
    return { total, published, drafts };
  }, [posts]);

  const statusDonutData = useMemo(() => {
    const counts = {
      Drafts: posts.filter((p) => p.status === 'draft').length,
      Scheduled: posts.filter((p) => p.status === 'scheduled').length,
      Publishing: posts.filter((p) => p.status === 'publishing').length,
      Published: posts.filter((p) => p.status === 'published').length,
      Failed: posts.filter((p) => p.status === 'failed').length,
    };
    return [
      { name: 'Drafts', value: counts.Drafts, color: '#f59e0b' },
      { name: 'Scheduled', value: counts.Scheduled, color: '#06b6d4' },
      { name: 'Publishing', value: counts.Publishing, color: '#6366f1' },
      { name: 'Published', value: counts.Published, color: '#10b981' },
      { name: 'Failed', value: counts.Failed, color: '#ef4444' },
    ];
  }, [posts]);

  const activityData = useMemo(() => {
    const days = 14;
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - (days - 1));
    start.setHours(0, 0, 0, 0);

    const buckets = new Map<string, number>();
    for (let i = 0; i < days; i += 1) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const key = d.toISOString().slice(0, 10);
      buckets.set(key, 0);
    }

    posts.forEach((p) => {
      const created = p.created_at ? new Date(p.created_at) : null;
      if (!created || Number.isNaN(created.getTime())) return;
      const createdKey = new Date(created.getFullYear(), created.getMonth(), created.getDate())
        .toISOString()
        .slice(0, 10);
      if (!buckets.has(createdKey)) return;
      buckets.set(createdKey, (buckets.get(createdKey) || 0) + 1);
    });

    return Array.from(buckets.entries()).map(([key, count]) => ({
      day: key.slice(5).replace('-', '/'),
      count,
    }));
  }, [posts]);

  const recentPosts = useMemo(() => posts.slice(0, 3), [posts]);

  const followerCount = profileInsights?.metrics?.followers ?? 0;
  const connectionCount = profileInsights?.metrics?.connections ?? 0;
  const avgWordCount = profileInsights?.content?.avg_word_count ?? 0;
  const lastPublishedAt = profileInsights?.content?.last_published_at ?? null;
  const recentTopics = profileInsights?.content?.recent_topics ?? [];

  const handleGenerate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setLoadingTitle('Generating Post');
    setLoadingText('AI is crafting your content...');
    try {
      const authToken = await getToken().catch(() => null);
      const data = await generatePost({
        topic,
        additional_context: context.trim() || null,
      }, { authToken });

      if (data.success) {
        setCurrentPost(data.post);
        setWordCount(data.post.content.split(/\s+/).length);
        setTopic('');
        setContext('');
        await loadPosts(filter ?? undefined);

        if (data.image?.error) {
          setImageError(data.image.error);
        } else {
          setImageError(null);
        }
      }
    } catch (error) {
      showToast((error as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestTopics = async () => {
    const occupationClean = occupation.trim();
    if (!occupationClean) {
      showToast('Please enter your occupation / work field first.', 'warning');
      return;
    }

    try {
      setIsSuggestingTopics(true);
      setSuggestTopicsError(null);
      const authToken = await getToken().catch(() => null);
      const data = await suggestTopics(
        { occupation: occupationClean, limit: 8 },
        { authToken },
      );
      if (data.success) {
        setSuggestedTopics(data.topics || []);
        if (!topic.trim() && data.topics?.length) {
          setTopic(data.topics[0]);
        }
      }
    } catch (error) {
      setSuggestTopicsError((error as Error).message);
    } finally {
      setIsSuggestingTopics(false);
    }
  };

  const handlePublish = async () => {
    if (!currentPost) return;
    const confirmed = await showModal({
      title: 'Publish to LinkedIn',
      message: 'Ready to publish this to LinkedIn?',
      confirmText: 'Publish',
      cancelText: 'Cancel',
      onConfirm: () => {},
    });
    if (!confirmed) return;
    setLoading(true);
    setLoadingTitle('Publishing');
    setLoadingText('Sending to LinkedIn...');
    try {
      const result = await publishPost(currentPost.id);
      showToast(result.message, 'success');
      await loadPosts(filter ?? undefined);
      setCurrentPost(null);
      setImagePreview(null);
    } catch (error) {
      showToast((error as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSchedule = async () => {
    if (!currentPost) return;
    if (!scheduleFor) return;

    const scheduled = new Date(scheduleFor);
    if (Number.isNaN(scheduled.getTime())) {
      showToast('Invalid schedule time.', 'error');
      return;
    }
    if (scheduled.getTime() <= Date.now()) {
      showToast('Schedule time must be in the future.', 'warning');
      return;
    }

    setLoading(true);
    setLoadingTitle('Scheduling');
    setLoadingText('Setting up your scheduled publish…');
    try {
      const result = await schedulePost(currentPost.id, {
        scheduled_for: scheduled.toISOString(),
        visibility: scheduleVisibility,
      });
      if (result.success) {
        showToast('Post scheduled.', 'success');
        await loadPosts(filter ?? undefined);
        setCurrentPost(result.post);
      }
    } catch (error) {
      showToast((error as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!currentPost) return;
    setLoading(true);
    setLoadingTitle('Saving Draft');
    setLoadingText('Updating your post...');
    try {
      const result = await updatePost(currentPost.id, { status: 'draft' });
      if (result.success) {
        await loadPosts(filter ?? undefined);
        showToast('Draft saved.', 'success');
      }
    } catch (error) {
      showToast((error as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailPost = async () => {
    if (!currentPost) return;
    const defaultEmail = user?.primaryEmailAddress?.emailAddress ?? '';
    const recipient = await showInput({
      title: 'Send draft by email',
      label: 'Email address',
      placeholder: 'email@example.com',
      defaultValue: defaultEmail,
      type: 'email',
    });
    if (!recipient) return;

    setLoading(true);
    setLoadingTitle('Sending Email');
    setLoadingText('Delivering your LinkedIn draft...');
    try {
      const payload = {
        recipients: [recipient],
        subject: `LinkedIn Draft: ${currentPost.topic}`,
        include_image: Boolean(currentPost.image_url || currentPost.image_base64),
      };
      const result = await emailPost(currentPost.id, payload);
      showToast(result.message, 'success');
    } catch (error) {
      showToast((error as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleEditContent = async () => {
    if (!currentPost) return;
    const updated = await showInput({
      title: 'Edit post content',
      label: 'Content',
      defaultValue: currentPost.content,
      placeholder: 'Your post content...',
    });
    if (updated) {
      try {
        const result = await updatePost(currentPost.id, { content: updated });
        if (result.success) {
          setCurrentPost(result.post);
          setWordCount(updated.split(/\s+/).length);
          await loadPosts(filter ?? undefined);
          showToast('Post updated.', 'success');
        }
      } catch (error) {
        showToast((error as Error).message, 'error');
      }
    }
  };

  const handleGenerateImage = async () => {
    if (!currentPost) return;
    setLoading(true);
    setLoadingTitle('Generating Image');
    setLoadingText('Hugging Face is painting your story...');
    try {
      const data = await generateImage(currentPost.topic);
      if (data.success) {
        setCurrentPost((prev) =>
          prev
            ? {
                ...prev,
                image_url: data.image_url,
                image_storage_path: data.storage_path,
                image_mime_type: data.mime_type,
              }
            : prev,
        );
        await updatePost(currentPost.id, {
          image_url: data.image_url,
          image_storage_path: data.storage_path,
          image_mime_type: data.mime_type,
        });
        setImageError(null);
      }
    } catch (error) {
      setImageError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePost = async (postId: number) => {
    const confirmed = await showModal({
      title: 'Delete post',
      message: 'Are you sure you want to delete this post? This cannot be undone.',
      confirmText: 'Delete',
      cancelText: 'Cancel',
      variant: 'danger',
      onConfirm: () => {},
    });
    if (!confirmed) return;
    try {
      const result = await deletePost(postId);
      if (result.success) {
        await loadPosts(filter ?? undefined);
        showToast('Post deleted.', 'success');
      }
    } catch (error) {
      showToast((error as Error).message, 'error');
    }
  };

  const greeting =
    user?.firstName ||
    user?.username ||
    user?.primaryEmailAddress?.emailAddress ||
    'Member';

  const linkedInConnected = isLinkedInStatusLoading ? null : (linkedinStatus?.authenticated ?? null);

  const handleNavClick = (id: Section) => {
    setActiveSection(id);
    setMobileNavOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900 md:flex">
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 z-20 md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 w-72 md:w-64 bg-white/75 dark:bg-slate-800/75 border-r border-slate-200/70 dark:border-slate-700/70 z-30 flex flex-col transition-transform duration-300 backdrop-blur-xl',
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full',
          'md:translate-x-0 md:static md:flex md:h-screen md:sticky md:top-0'
        )}
      >
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-24 -left-24 h-56 w-56 rounded-full bg-indigo-400/15 blur-3xl" />
          <div className="absolute top-28 -right-24 h-56 w-56 rounded-full bg-cyan-400/10 blur-3xl" />
        </div>

        <div className="relative p-6 flex-1 overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center justify-center w-full">
              <img
                src={BRAND.logoSrc}
                alt={`${BRAND.appName} logo`}
                className="h-12 w-auto max-w-[200px] object-contain"
              />
            </div>
            <button
              type="button"
              className="md:hidden inline-flex items-center justify-center h-10 w-10 rounded-xl border border-slate-200/70 dark:border-slate-700/70 bg-white/70 dark:bg-slate-700/70 text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-600 transition"
              onClick={() => setMobileNavOpen(false)}
              aria-label="Close sidebar"
              title="Close"
            >
              ✕
            </button>
          </div>
          <button
            type="button"
            className="md:hidden hidden"
            onClick={() => setMobileNavOpen(false)}
          >
            Close
          </button>

          <p className="text-[11px] uppercase tracking-[0.35em] text-slate-400 dark:text-slate-500 font-semibold mb-3">
            Navigation
          </p>
          <nav className="space-y-1.5">
            {sections.map(({ id, label, icon: Icon }) => {
              const isActive = activeSection === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => handleNavClick(id)}
                  className={clsx(
                    'group w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-semibold transition relative',
                    isActive
                      ? 'bg-slate-900 dark:bg-slate-700 text-white shadow-lg shadow-slate-900/20'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-white/70 dark:hover:bg-slate-700/50',
                  )}
                >
                  <span
                    className={clsx(
                      'h-9 w-9 rounded-xl flex items-center justify-center transition',
                      isActive ? 'bg-white/10' : 'bg-slate-100 dark:bg-slate-700 group-hover:bg-slate-200 dark:group-hover:bg-slate-600',
                    )}
                  >
                    <Icon className={clsx('h-4 w-4', isActive ? 'text-white' : 'text-slate-700 dark:text-slate-300')} />
                  </span>
                  <span className="flex-1 text-left">{label}</span>
                  {isActive && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(16,185,129,0.55)]" />
                  )}
                </button>
              );
            })}

            <button
              type="button"
              onClick={() => navigate('/settings')}
              className="group w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-white/70 dark:hover:bg-slate-700/50 transition"
            >
              <span className="h-9 w-9 rounded-xl bg-slate-100 dark:bg-slate-700 group-hover:bg-slate-200 dark:group-hover:bg-slate-600 flex items-center justify-center transition">
                <SettingsIcon className="h-4 w-4" />
              </span>
              <span className="flex-1 text-left">Settings</span>
            </button>
          </nav>
        </div>
        <div className="relative mt-auto p-6 border-t border-slate-200/60 dark:border-slate-700/60">
          <div className="ios-card bg-white dark:bg-slate-800/70 dark:bg-slate-800/70 rounded-2xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden">
                <UserButton appearance={{ elements: { avatarBox: 'w-10 h-10' } }} />
              </div>
              <div className="text-sm min-w-0">
                <p className="font-semibold text-slate-900 dark:text-slate-100 truncate" title={greeting}>
                  {greeting}
                </p>
                <p
                  className={clsx(
                    'text-xs font-semibold',
                    linkedInConnected === null
                      ? 'text-slate-500 dark:text-slate-400'
                      : linkedInConnected
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-rose-600 dark:text-rose-400',
                  )}
                >
                  {linkedInConnected === null
                    ? 'Checking LinkedIn...'
                    : linkedInConnected
                      ? 'LinkedIn Connected'
                      : 'LinkedIn Not Connected'}
                </p>
              </div>
            </div>
          </div>
          {linkedInConnected === false && (
            <button
              type="button"
              onClick={() => openLinkedInConnect({ clerkUserId: user?.id })}
              className="mt-4 w-full py-2.5 text-sm font-semibold rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500 transition shadow-lg shadow-indigo-600/20"
            >
              Connect LinkedIn
            </button>
          )}
        </div>
      </aside>

      <main className="min-h-screen relative overflow-y-auto md:flex-1 bg-slate-100 dark:bg-slate-900">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-indigo-400/20 blur-3xl" />
          <div className="absolute top-40 -left-24 h-72 w-72 rounded-full bg-cyan-400/15 blur-3xl" />
          <div className="absolute bottom-0 right-10 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
        </div>
        <div className="relative max-w-6xl mx-auto p-6 pb-28 md:pb-6 space-y-10">
          <div className="md:hidden grid grid-cols-[auto,1fr,auto] items-center gap-3">
            <button className="p-2 text-slate-600 dark:text-slate-300" onClick={() => setMobileNavOpen(true)}>
              <Menu className="h-6 w-6" />
            </button>
            <img
              src={BRAND.logoSrc}
              alt={`${BRAND.appName} logo`}
              className="justify-self-center h-11 w-auto max-w-[220px] object-contain"
            />
            <UserButton />
          </div>
          <div className="flex items-center justify-end gap-4">
            <div className="text-right">
              <p className="text-xs uppercase text-slate-400 dark:text-slate-500 font-semibold tracking-[0.3em]">
                Welcome back
              </p>
              <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">Hi, {greeting}</p>
            </div>
            <ThemeToggle size="md" />
            <UserButton
              appearance={{
                elements: { avatarBox: 'w-10 h-10' },
              }}
            />
            <button
              type="button"
              onClick={() => signOut({ redirectUrl: '/auth' })}
              className="px-4 py-2 text-xs font-semibold border border-slate-200 dark:border-slate-700 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
            >
              Log out
            </button>
          </div>

          {linkedInConnected === false && (
            <section className="relative isolate rounded-3xl overflow-hidden shadow-2xl">
              <img
                src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80"
                alt="Workspace"
                className="absolute inset-0 h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-slate-900/90 via-slate-900/70 to-slate-900/40" />
              <div className="relative z-10 p-8 md:p-12 flex flex-col lg:flex-row gap-10 items-start lg:items-center text-white">
                <div className="max-w-2xl">
                  <p className="uppercase tracking-[0.4em] text-xs text-emerald-300 mb-3">
                    Unified Access
                  </p>
                  <h2 className="text-3xl md:text-4xl font-bold leading-tight">
                    Sign in once. Automate everywhere.
                  </h2>
                  <p className="mt-4 text-slate-200 text-base md:text-lg">
                    Authenticate with Clerk, then connect your LinkedIn account to ship posts
                    faster.
                  </p>
                  <div className="flex flex-wrap gap-4 mt-6">
                    <button
                      type="button"
                      onClick={() => navigate('/settings')}
                      className="px-6 py-3 rounded-2xl bg-white/10 border border-white/20 text-white font-medium hover:bg-white/20 transition"
                    >
                      LinkedIn Settings
                    </button>
                    <button
                      type="button"
                      onClick={() => openLinkedInConnect({ clerkUserId: user?.id })}
                      className="px-6 py-3 rounded-2xl bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                    >
                      Connect LinkedIn
                    </button>
                  </div>
                </div>
              </div>
            </section>
          )}

          {activeSection === 'dashboard' && (
            <section className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Dashboard</h2>
                  <p className="text-slate-500 dark:text-slate-400">Welcome back to your content command center.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSection('generate')}
                  className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl font-medium shadow hover:bg-blue-700 transition"
                >
                  <Plus className="h-4 w-4" />
                  New Post
                </button>
              </div>

              {isPostsLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Skeleton className="h-36 w-full rounded-2xl" />
                  <Skeleton className="h-36 w-full rounded-2xl" />
                  <Skeleton className="h-36 w-full rounded-2xl" />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <StatCard
                    title="Total Posts"
                    value={stats.total}
                    badge="Total"
                    icon={FileEdit}
                    iconColor="text-blue-600"
                    iconBg="bg-blue-50"
                  />
                  <StatCard
                    title="Published"
                    value={stats.published}
                    badge="Live"
                    icon={CheckCircle2}
                    iconColor="text-emerald-600"
                    iconBg="bg-emerald-50"
                  />
                  <StatCard
                    title="Drafts"
                    value={stats.drafts}
                    badge="Pending"
                    icon={Clock3}
                    iconColor="text-amber-600"
                    iconBg="bg-amber-50"
                  />
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl lg:col-span-2">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <p className="text-xs uppercase text-slate-400 font-semibold tracking-[0.3em]">
                        Momentum
                      </p>
                      <h3 className="text-lg font-bold text-slate-900">Post activity (last 14 days)</h3>
                    </div>
                    <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-full">
                      Trendline
                    </span>
                  </div>
                  <ActivityAreaChart data={activityData} />
                </div>
                <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <p className="text-xs uppercase text-slate-400 font-semibold tracking-[0.3em]">
                        Status Mix
                      </p>
                      <h3 className="text-lg font-bold text-slate-900">Pipeline</h3>
                    </div>
                    <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-full">
                      Live
                    </span>
                  </div>
                  <StatusDonutChart data={statusDonutData} />
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
                    {statusDonutData
                      .filter((d) => d.value > 0)
                      .slice(0, 4)
                      .map((d) => (
                        <div key={d.name} className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} />
                          <span className="truncate">{d.name}</span>
                          <span className="ml-auto font-semibold text-slate-700">{d.value}</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              {isInsightsLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <Skeleton className="h-56 w-full rounded-2xl" />
                  <Skeleton className="h-56 w-full rounded-2xl" />
                  <Skeleton className="h-56 w-full rounded-2xl" />
                </div>
              ) : profileInsights ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase text-slate-400 font-semibold tracking-[0.3em]">
                          Profile Summary
                        </p>
                        <h3 className="text-lg font-bold text-slate-900">
                          {profileInsights.profile?.first_name || profileInsights.profile?.last_name
                            ? `${profileInsights.profile?.first_name ?? ''} ${profileInsights.profile?.last_name ?? ''}`.trim()
                            : 'LinkedIn Member'}
                        </h3>
                        {profileInsights.profile?.headline && (
                          <p className="text-sm text-slate-500">{profileInsights.profile.headline}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={loadProfileInsights}
                        className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-300 transition"
                        title="Refresh LinkedIn data"
                      >
                        <RefreshCcw className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed">
                      {profileInsights.summary || 'LinkedIn profile data unavailable.'}
                    </p>
                    {profileInsights.profile?.bio && (
                      <p className="text-xs text-slate-400 line-clamp-3">{profileInsights.profile.bio}</p>
                    )}
                    <p className="text-xs text-slate-400">
                      Synced {profileInsights.timestamp ? formatDate(profileInsights.timestamp) : 'Not yet'}
                    </p>
                  </div>
                  <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl space-y-4">
                    <p className="text-sm font-semibold text-slate-900">Audience Metrics</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-slate-500 uppercase">Followers</p>
                        <p className="text-3xl font-bold text-slate-900">{formatMetric(followerCount)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 uppercase">Connections</p>
                        <p className="text-3xl font-bold text-slate-900">{formatMetric(connectionCount)}</p>
                      </div>
                    </div>
                    <div className="text-xs text-slate-400">
                      Data sourced via LinkedIn network sizes API.
                    </div>
                  </div>
                  <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl space-y-4">
                    <p className="text-sm font-semibold text-slate-900">Content Analytics</p>
                    <div className="space-y-2 text-sm text-slate-600">
                      <p>
                        Avg Word Count:{' '}
                        <span className="font-semibold text-slate-900">{avgWordCount || '—'}</span>
                      </p>
                      <p>
                        Published Posts:{' '}
                        <span className="font-semibold text-slate-900">{profileInsights.content?.published ?? 0}</span>
                      </p>
                      <p>
                        Last Published:{' '}
                        <span className="font-semibold text-slate-900">{formatDate(lastPublishedAt)}</span>
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-slate-400 mb-2">Recent Topics</p>
                      <div className="flex flex-wrap gap-2">
                        {recentTopics.length === 0 ? (
                          <span className="text-xs text-slate-400">No topics yet</span>
                        ) : (
                          recentTopics.map((topic) => (
                            <span
                              key={topic}
                              className="px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium"
                            >
                              {topic}
                            </span>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {insightsError && (
                <div className="ios-card bg-rose-50 border border-rose-100 text-rose-700 p-4 rounded-2xl flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold">LinkedIn analytics unavailable</p>
                    <p className="text-xs">{insightsError}</p>
                  </div>
                  <button
                    type="button"
                    onClick={loadProfileInsights}
                    className="text-xs font-semibold px-3 py-1.5 rounded-full bg-white text-rose-600 border border-rose-200 hover:border-rose-300"
                  >
                    Retry
                  </button>
                </div>
              )}

              <div className="ios-card bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="font-bold text-slate-900">Recent Posts</h3>
                  <button
                    type="button"
                    onClick={() => setActiveSection('posts')}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    View All
                  </button>
                </div>
                <div>
                  {recentPosts.length === 0 ? (
                    <div className="p-6 text-center text-slate-400 text-sm">No recent activity</div>
                  ) : (
                    recentPosts.map((post) => (
                      <div
                        key={post.id}
                        className="p-4 hover:bg-slate-50 transition flex items-center justify-between"
                      >
                        <div>
                          <p className="font-medium text-slate-900 text-sm truncate max-w-[220px]">
                            {post.topic}
                          </p>
                          <p className="text-xs text-slate-500">
                            {new Date(post.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <span
                          className={clsx(
                            'text-xs font-semibold',
                            post.status === 'published'
                              ? 'text-emerald-600'
                              : 'text-amber-600',
                          )}
                        >
                          {post.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>
          )}

          {activeSection === 'generate' && (
            <section className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Generate Content</h2>
                <p className="text-slate-500">Use AI to craft the perfect LinkedIn post.</p>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <form onSubmit={handleGenerate} className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl space-y-5">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      Your Work Occupation
                    </label>
                    <input
                      type="text"
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                      placeholder="e.g. Civil Engineer, Sales Manager, Software Developer"
                      value={occupation}
                      onChange={(e) => setOccupation(e.target.value)}
                      required
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={handleSuggestTopics}
                      disabled={isSuggestingTopics || !occupation.trim()}
                      className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <Sparkles className="h-4 w-4" />
                      {isSuggestingTopics ? 'Generating topics...' : 'Suggest Topics'}
                    </button>
                    <p className="text-xs text-slate-500">
                      Get fresh topic ideas tailored to your field (trend-aware).
                    </p>
                  </div>

                  {isSuggestingTopics ? (
                    <div className="space-y-3">
                      <Skeleton className="h-5 w-40" />
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                      </div>
                    </div>
                  ) : suggestedTopics.length ? (
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-slate-700">Pick a topic</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {suggestedTopics.map((t) => (
                          <button
                            key={t}
                            type="button"
                            onClick={() => setTopic(t)}
                            className={clsx(
                              'text-left px-4 py-3 rounded-xl border text-sm font-medium transition',
                              topic === t
                                ? 'border-blue-300 bg-blue-50 text-blue-800'
                                : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700',
                            )}
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {suggestTopicsError && (
                    <p className="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-xl p-4">
                      {suggestTopicsError}
                    </p>
                  )}

                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      Selected Topic <span className="text-slate-400 font-normal">(editable)</span>
                    </label>
                    <input
                      type="text"
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                      placeholder="Pick a suggested topic above (or type your own)"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      Additional Context{' '}
                      <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <textarea
                      rows={4}
                      className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none resize-none"
                      placeholder="Specific tone, key points to include, or target audience..."
                      value={context}
                      onChange={(e) => setContext(e.target.value)}
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition flex items-center justify-center gap-2 shadow shadow-blue-600/20"
                  >
                    <Sparkles className="h-5 w-5" />
                    Generate Magic
                  </button>
                </form>

                <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl flex flex-col gap-5">
                  {!currentPost ? (
                    <div className="flex flex-col items-center justify-center text-slate-400 py-16">
                      <LayoutDashboard className="w-10 h-10 mb-3" />
                      <p className="font-medium">Generated content will appear here</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div>
                          <p className="text-xs uppercase text-slate-400 font-semibold tracking-[0.3em]">
                            LinkedIn Preview
                          </p>
                          <h3 className="text-lg font-semibold text-slate-900">{currentPost.topic}</h3>
                        </div>
                        <div className="text-right text-xs text-slate-400">
                          <p>{wordCount} words</p>
                          <p className="font-medium text-slate-500">AI copy &amp; visual</p>
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-100 dark:border-slate-700 bg-slate-50/60 p-5 space-y-5">
                        <div className="flex gap-3 items-center">
                          <div className="w-12 h-12 bg-slate-200 rounded-full" />
                          <div>
                            <p className="font-semibold text-slate-900">{greeting}</p>
                            <p className="text-xs text-slate-500">Preview · LinkedIn Feed</p>
                          </div>
                        </div>
                        <div className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                          {currentPost.content}
                        </div>
                        <div className="rounded-2xl overflow-hidden border border-slate-200 bg-white">
                          {imagePreview ? (
                            <img
                              src={imagePreview}
                              alt="Generated visual"
                              className="w-full h-64 object-cover"
                            />
                          ) : (
                            <div className="h-64 flex items-center justify-center text-sm text-slate-400 bg-slate-50">
                              Image preview will appear automatically
                            </div>
                          )}
                        </div>
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={handleGenerateImage}
                            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-600 border border-slate-200 rounded-xl hover:bg-slate-50 transition"
                          >
                            <RefreshCcw className="h-4 w-4" />
                            Refresh Image
                          </button>
                        </div>
                        {imageError && (
                          <p className="text-sm text-rose-500">Image error: {imageError}</p>
                        )}
                        <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-200 pt-3">
                          <span>Preview only</span>
                          <span className="inline-flex items-center gap-1">
                            <Sparkles className="h-3 w-3" />
                            AI Generated
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-3 flex-wrap">
                        <button
                          type="button"
                          onClick={handleEditContent}
                          className="flex-1 min-w-[120px] py-2.5 bg-slate-100 text-slate-700 rounded-lg font-medium hover:bg-slate-200 flex items-center justify-center gap-2"
                        >
                          <Pencil className="h-4 w-4" />
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveDraft}
                          className="flex-1 min-w-[120px] py-2.5 bg-amber-50 text-amber-700 rounded-lg font-medium hover:bg-amber-100 flex items-center justify-center gap-2"
                        >
                          <Save className="h-4 w-4" />
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={handleEmailPost}
                          className="flex-1 min-w-[120px] py-2.5 bg-blue-50 text-blue-700 rounded-lg font-medium hover:bg-blue-100 flex items-center justify-center gap-2"
                        >
                          <Mail className="h-4 w-4" />
                          Email
                        </button>
                        <div className="flex-[2] min-w-[240px] flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                          <input
                            type="datetime-local"
                            className="flex-1 bg-transparent text-sm text-slate-700 outline-none"
                            value={scheduleFor}
                            onChange={(e) => setScheduleFor(e.target.value)}
                          />
                          <select
                            className="bg-transparent text-sm text-slate-600 outline-none"
                            value={scheduleVisibility}
                            onChange={(e) =>
                              setScheduleVisibility(e.target.value as 'PUBLIC' | 'CONNECTIONS')
                            }
                          >
                            <option value="PUBLIC">Public</option>
                            <option value="CONNECTIONS">Connections</option>
                          </select>
                          <button
                            type="button"
                            onClick={handleSchedule}
                            className="px-3 py-1.5 rounded-md bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800"
                          >
                            Schedule
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={handlePublish}
                          className="flex-1 min-w-[120px] py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 flex items-center justify-center gap-2 shadow shadow-emerald-600/20"
                        >
                          <Send className="h-4 w-4" />
                          Publish
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>

            </section>
          )}

          {activeSection === 'posts' && (
            <section className="space-y-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Post Library</h2>
                  <p className="text-slate-500">Manage your drafted and published content.</p>
                </div>
                <div className="bg-slate-100 p-1 rounded-xl inline-flex">
                  {(['all', 'draft', 'scheduled', 'published', 'failed'] as const).map((status) => (
                    <button
                      key={status}
                      type="button"
                      onClick={() =>
                        setFilter(status === 'all' ? null : (status as PostStatus))
                      }
                      className={clsx(
                        'px-4 py-1.5 rounded-lg text-sm font-medium transition',
                        (status === 'all' && filter === null) || filter === status
                          ? 'bg-white shadow text-slate-900'
                          : 'text-slate-600',
                      )}
                    >
                      {status === 'all'
                        ? 'All'
                        : status.charAt(0).toUpperCase() + status.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                {posts.length === 0 ? (
                  <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-slate-300">
                    <Ghost className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500">No posts found.</p>
                  </div>
                ) : (
                  posts.map((post) => (
                    <div
                      key={post.id}
                      className="ios-card bg-white dark:bg-slate-800 p-5 rounded-2xl hover:shadow-md transition group"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span
                              className={clsx(
                                'px-2.5 py-0.5 text-xs font-semibold rounded-full',
                                post.status === 'published'
                                  ? 'bg-emerald-100 text-emerald-700'
                                  : post.status === 'draft'
                                  ? 'bg-amber-100 text-amber-700'
                                  : 'bg-slate-100 text-slate-700',
                              )}
                            >
                              {post.status}
                            </span>
                            <span className="text-xs text-slate-400">
                              {new Date(post.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <h3 className="font-bold text-slate-900 mb-1">{post.topic}</h3>
                          <p className="text-sm text-slate-600 line-clamp-2">{post.content}</p>
                        </div>
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                          {post.status !== 'published' && (
                            <button
                              type="button"
                              onClick={() => {
                                setCurrentPost(post);
                                setActiveSection('generate');
                              }}
                              className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg"
                            >
                              <Send className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDeletePost(post.id)}
                            className="p-2 text-rose-600 hover:bg-rose-50 rounded-lg"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          )}
        </div>

        <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 px-4 pb-4">
          <div className="ios-card bg-white dark:bg-slate-800/85 border border-slate-200 rounded-2xl px-2 py-2 backdrop-blur">
            <div className="grid grid-cols-4 gap-1">
              {sections.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => handleNavClick(id)}
                  className={clsx(
                    'flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-[11px] font-semibold transition',
                    activeSection === id ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50',
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => navigate('/settings')}
                className="flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 transition"
              >
                <SettingsIcon className="h-5 w-5" />
                Settings
              </button>
            </div>
          </div>
        </nav>

        {loading && (
          <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-40 flex items-center justify-center">
            <div className="bg-white p-8 rounded-3xl shadow-2xl border border-slate-100 dark:border-slate-700 text-center max-w-sm w-full mx-4">
              <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <RefreshCcw className="animate-spin h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-2">{loadingTitle}</h3>
              <p className="text-slate-500">{loadingText}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const StatCard = ({
  title,
  value,
  badge,
  icon: Icon,
  iconColor,
  iconBg,
}: {
  title: string;
  value: number;
  badge: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
}) => (
  <div className="ios-card bg-white dark:bg-slate-800 p-6 rounded-2xl">
    <div className="flex items-center justify-between mb-4">
      <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', iconBg, iconColor)}>
        <Icon className="w-5 h-5" />
      </div>
      <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-full">
        {badge}
      </span>
    </div>
    <h3 className="text-3xl font-bold text-slate-900">{value}</h3>
    <p className="text-sm text-slate-500 mt-1">{title}</p>
  </div>
);

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg
    className={clsx('h-4 w-4', className)}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .69.28 1.35.76 1.82.48.48 1.14.76 1.82.76H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
  </svg>
);

export default DashboardPage;

