'use client';

import { useState } from 'react';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';

export default function Home() {
  const [section, setSection] = useState<'data-analysis' | 'quality-control'>('data-analysis');

  return (
    <LandingPage
      section={section}
      onSectionChange={setSection}
    >
      {section === 'data-analysis' ? (
        <Dashboard />
      ) : (
        <div style={{ padding: 24, color: 'var(--text-secondary)' }}>
          Quality control — coming soon.
        </div>
      )}
    </LandingPage>
  );
}
