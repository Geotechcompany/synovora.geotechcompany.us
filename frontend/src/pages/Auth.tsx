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
      <div className="relative flex-1 min-h-[320px]">
        <img
          src={heroImage}
          alt="Workspace"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-900/90 via-slate-900/70 to-slate-900/40" />
        <div className="relative z-10 h-full flex flex-col justify-center px-8 py-12 lg:px-16 max-w-2xl">
          <div className="flex justify-center mb-10">
            <img
              src={BRAND.logoSrc}
              alt={`${BRAND.appName} logo`}
              className="h-20 w-auto max-w-[360px] object-contain"
            />
          </div>
          <p className="uppercase tracking-[0.4em] text-emerald-300 text-xs mb-4">
            Unified Access
          </p>
          <h1 className="text-4xl font-bold leading-tight mb-4">
            Sign in once. Automate everywhere.
          </h1>
          <p className="text-slate-200 text-lg">
            Authenticate with Clerk for a luxurious onboarding experience, then
            connect your LinkedIn account to ship posts faster.
          </p>
          <div className="flex gap-4 mt-8 flex-wrap">
            <button
              onClick={() => setView('signin')}
              className={`px-6 py-3 rounded-2xl font-semibold transition ${
                view === 'signin'
                  ? 'bg-white text-slate-900'
                  : 'bg-white/10 border border-white/40'
              }`}
            >
              Sign in
            </button>
            <button
              onClick={() => setView('signup')}
              className={`px-6 py-3 rounded-2xl font-semibold transition ${
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

      <div className="flex-1 flex items-center justify-center bg-slate-900">
        <div className="w-full max-w-md px-6 py-10">
          <div className="rounded-3xl p-8">
            {view === 'signin' ? (
              <SignIn
                appearance={{
                  elements: {
                    footer: 'hidden',
                    headerTitle: 'hidden',
                    card: 'border border-slate-100 shadow-none rounded-2xl',
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

