import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ClerkProvider } from '@clerk/clerk-react';

import './index.css';
import App from './App.tsx';

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!clerkKey) {
  throw new Error(
    'Missing VITE_CLERK_PUBLISHABLE_KEY environment variable for Clerk.',
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider publishableKey={clerkKey} afterSignOutUrl="/auth">
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ClerkProvider>
  </StrictMode>,
);
