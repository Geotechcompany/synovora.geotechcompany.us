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
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50">
      {/* Hero Section - Hidden on mobile, visible on tablet+ */}
      <div className="hidden md:block relative flex-1 min-h-[320px] lg:min-h-screen">
        <img
          src={heroImage}
          alt="Workspace"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-900/95 via-slate-900/85 to-slate-900/60" />
        <div className="relative z-10 h-full flex flex-col justify-center px-6 py-8 md:px-8 lg:px-16 max-w-2xl">
          <div className="flex justify-center mb-6 md:mb-10">
            <img
              src={BRAND.logoSrc}
              alt={`${BRAND.appName} logo`}
              className="h-24 md:h-32 lg:h-40 w-auto max-w-[400px] md:max-w-[500px] lg:max-w-[600px] object-contain drop-shadow-lg"
              onError={(e) => {
                // Fallback if image fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
              }}
            />
          </div>
          <p className="uppercase tracking-[0.3em] md:tracking-[0.4em] text-emerald-400 text-[10px] md:text-xs mb-3 md:mb-4 font-semibold">
            Welcome to Synvora
          </p>
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold leading-tight mb-3 md:mb-4 text-white">
            Create and schedule LinkedIn content with AI
          </h1>
          <p className="text-slate-200 text-sm md:text-base lg:text-lg leading-relaxed">
            Generate engaging posts, schedule them automatically, and grow your professional network. 
            All powered by intelligent automation.
          </p>
          <div className="flex gap-3 md:gap-4 mt-6 md:mt-8 flex-wrap">
            <button
              onClick={() => setView('signin')}
              className={`px-5 py-2.5 md:px-6 md:py-3 rounded-xl md:rounded-2xl text-sm md:text-base font-semibold transition ${
                view === 'signin'
                  ? 'bg-white text-slate-900 shadow-lg'
                  : 'bg-white/10 border border-white/30 text-white hover:bg-white/20'
              }`}
            >
              Sign in
            </button>
            <button
              onClick={() => setView('signup')}
              className={`px-5 py-2.5 md:px-6 md:py-3 rounded-xl md:rounded-2xl text-sm md:text-base font-semibold transition ${
                view === 'signup'
                  ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                  : 'bg-white/10 border border-white/30 text-white hover:bg-white/20'
              }`}
            >
              Get started
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Header - Only visible on mobile */}
      <div className="md:hidden bg-white px-6 py-6 border-b border-slate-200">
        <div className="flex items-center justify-center mb-6">
          <img
            src={BRAND.logoSrc}
            alt={`${BRAND.appName} logo`}
            className="h-16 md:h-20 w-auto object-contain drop-shadow-sm"
            onError={(e) => {
              // Fallback if image fails to load
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        </div>
        <div className="text-center">
          <p className="uppercase tracking-[0.3em] text-emerald-600 text-[10px] mb-2 font-semibold">
            Welcome to Synvora
          </p>
          <h1 className="text-xl font-bold leading-tight mb-2 text-slate-900">
            Create and schedule LinkedIn content with AI
          </h1>
        </div>
        <div className="flex gap-3 mt-4 justify-center">
          <button
            onClick={() => setView('signin')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${
              view === 'signin'
                ? 'bg-slate-900 text-white shadow-md'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Sign in
          </button>
          <button
            onClick={() => setView('signup')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${
              view === 'signup'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Get started
          </button>
        </div>
      </div>

      {/* Form Section - Centered */}
      <div className="flex-1 flex items-center justify-center bg-slate-50 min-h-[calc(100vh-200px)] md:min-h-screen px-4 py-8">
        <div className="w-full max-w-md">
          {/* Logo on form section for desktop */}
          <div className="hidden md:flex justify-center mb-6">
            <img
              src={BRAND.logoSrc}
              alt={`${BRAND.appName} logo`}
              className="h-20 lg:h-24 w-auto object-contain"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
              }}
            />
          </div>
          {view === 'signin' ? (
            <SignIn
              appearance={{
                elements: {
                  footer: 'hidden',
                  headerTitle: 'hidden',
                  card: 'bg-white border border-slate-200 shadow-xl rounded-2xl',
                  rootBox: 'w-full',
                  formButtonPrimary: 'bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold py-2.5 rounded-lg transition shadow-md',
                  formFieldInput: 'text-slate-900 border-slate-200 focus:border-slate-900 focus:ring-slate-900',
                  formFieldLabel: 'text-slate-700 font-medium text-sm',
                  socialButtonsBlockButton: 'border-slate-200 hover:bg-slate-50 text-slate-700 font-medium',
                  formHeaderTitle: 'hidden',
                  formHeaderSubtitle: 'hidden',
                  identityPreviewText: 'text-slate-600',
                  identityPreviewEditButton: 'text-slate-900 hover:bg-slate-100',
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
                  card: 'bg-white border border-slate-200 shadow-xl rounded-2xl',
                  rootBox: 'w-full',
                  formButtonPrimary: 'bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold py-2.5 rounded-lg transition shadow-md',
                  formFieldInput: 'text-slate-900 border-slate-200 focus:border-slate-900 focus:ring-slate-900',
                  formFieldLabel: 'text-slate-700 font-medium text-sm',
                  socialButtonsBlockButton: 'border-slate-200 hover:bg-slate-50 text-slate-700 font-medium',
                  formHeaderTitle: 'hidden',
                  formHeaderSubtitle: 'hidden',
                  identityPreviewText: 'text-slate-600',
                  identityPreviewEditButton: 'text-slate-900 hover:bg-slate-100',
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
  );
};

export default AuthPage;

