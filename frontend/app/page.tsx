'use client';

import { useState } from 'react';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import QualityControl from './components/QualityControl';

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
        <QualityControl />
      )}
    </LandingPage>
  );
}
