import { useEffect, useState } from 'react';
import { SignIn, SignUp, useAuth } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';

import { BRAND } from '../config/brand';

const heroImage =
  'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80';

const AuthPage = () => {
  const { isSignedIn } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState<'signin' | 'signup'>('signin');

  useEffect(() => {
    if (isSignedIn) {
      navigate('/', { replace: true });
    }
  }, [isSignedIn, navigate]);

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-900 text-white">
      {/* Hero Section - Hidden on mobile, visible on tablet+ */}
      <div className="hidden md:block relative flex-1 min-h-[320px] lg:min-h-screen">
        <img
          src={heroImage}
          alt="Workspace"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-900/90 via-slate-900/70 to-slate-900/40" />
        <div className="relative z-10 h-full flex flex-col justify-center px-6 py-8 md:px-8 lg:px-16 max-w-2xl">
          <div className="flex justify-center mb-6 md:mb-10">
            <img
              src={BRAND.logoSrc}
              alt={`${BRAND.appName} logo`}
              className="h-16 md:h-20 w-auto max-w-[280px] md:max-w-[360px] object-contain"
            />
          </div>
          <p className="uppercase tracking-[0.3em] md:tracking-[0.4em] text-emerald-300 text-[10px] md:text-xs mb-3 md:mb-4">
            Unified Access
          </p>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold leading-tight mb-3 md:mb-4">
            Sign in once. Automate everywhere.
          </h1>
          <p className="text-slate-200 text-sm md:text-base lg:text-lg">
            Authenticate with Clerk for a luxurious onboarding experience, then
            connect your LinkedIn account to ship posts faster.
          </p>
          <div className="flex gap-3 md:gap-4 mt-6 md:mt-8 flex-wrap">
            <button
              onClick={() => setView('signin')}
              className={`px-5 py-2.5 md:px-6 md:py-3 rounded-xl md:rounded-2xl text-sm md:text-base font-semibold transition ${
                view === 'signin'
                  ? 'bg-white text-slate-900'
                  : 'bg-white/10 border border-white/40'
              }`}
            >
              Sign in
            </button>
            <button
              onClick={() => setView('signup')}
              className={`px-5 py-2.5 md:px-6 md:py-3 rounded-xl md:rounded-2xl text-sm md:text-base font-semibold transition ${
                view === 'signup'
                  ? 'bg-emerald-400 text-slate-900'
                  : 'bg-white/10 border border-white/30'
              }`}
            >
              Create account
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Header - Only visible on mobile */}
      <div className="md:hidden bg-slate-900 px-6 py-6 border-b border-slate-800">
        <div className="flex items-center justify-between mb-6">
          <img
            src={BRAND.logoSrc}
            alt={`${BRAND.appName} logo`}
            className="h-10 w-auto object-contain"
          />
        </div>
        <div className="text-center">
          <p className="uppercase tracking-[0.3em] text-emerald-300 text-[10px] mb-2">
            Unified Access
          </p>
          <h1 className="text-xl font-bold leading-tight mb-2">
            Sign in once. Automate everywhere.
          </h1>
        </div>
        <div className="flex gap-3 mt-4 justify-center">
          <button
            onClick={() => setView('signin')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${
              view === 'signin'
                ? 'bg-white text-slate-900'
                : 'bg-white/10 border border-white/40'
            }`}
          >
            Sign in
          </button>
          <button
            onClick={() => setView('signup')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${
              view === 'signup'
                ? 'bg-emerald-400 text-slate-900'
                : 'bg-white/10 border border-white/30'
            }`}
          >
            Create account
          </button>
        </div>
      </div>

      {/* Form Section */}
      <div className="flex-1 flex items-center justify-center bg-slate-900 min-h-[calc(100vh-200px)] md:min-h-screen">
        <div className="w-full max-w-md px-4 py-6 md:px-6 md:py-10">
          <div className="rounded-2xl md:rounded-3xl p-4 md:p-8">
            {view === 'signin' ? (
              <SignIn
                appearance={{
                  elements: {
                    footer: 'hidden',
                    headerTitle: 'hidden',
                    card: 'border border-slate-100 shadow-none rounded-2xl',
                    rootBox: 'w-full',
                    formButtonPrimary: 'bg-slate-900 hover:bg-slate-800 text-white',
                    formFieldInput: 'text-slate-900',
                    formFieldLabel: 'text-slate-700',
                    socialButtonsBlockButton: 'border-slate-200 hover:bg-slate-50',
                  },
                }}
                routing="virtual"
                signUpUrl="/auth"
                afterSignInUrl="/"
                afterSignUpUrl="/"
              />
            ) : (
              <SignUp
                appearance={{
                  elements: {
                    footer: 'hidden',
                    headerTitle: 'hidden',
                    card: 'border border-slate-100 shadow-none rounded-2xl',
                    rootBox: 'w-full',
                    formButtonPrimary: 'bg-slate-900 hover:bg-slate-800 text-white',
                    formFieldInput: 'text-slate-900',
                    formFieldLabel: 'text-slate-700',
                    socialButtonsBlockButton: 'border-slate-200 hover:bg-slate-50',
                  },
                }}
                routing="virtual"
                signInUrl="/auth"
                afterSignInUrl="/"
                afterSignUpUrl="/"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;

