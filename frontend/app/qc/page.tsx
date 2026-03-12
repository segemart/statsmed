'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { listPublicQCOperations, type PublicQCOperationSummary } from '../lib/api';
import styles from './PublicQC.module.css';
import logoImg from '../../Icon/NewIcon.png';

export default function PublicQCListPage() {
  const [operations, setOperations] = useState<PublicQCOperationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    listPublicQCOperations()
      .then(setOperations)
      .catch(() => setError('Failed to load public quality control panels.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <header className={styles.topBar}>
        <Link href="/" className={styles.logo}>
          <Image src={logoImg} alt="Statsmed" className={styles.logoIcon} width={36} height={36} priority />
          Statsmed
          <span className={styles.logoSubtitle}>Statistics for Medical Data</span>
        </Link>
      </header>

      <main className={styles.main}>
        <h1 className={styles.pageTitle}>Public Quality Control</h1>
        <p className={styles.pageSubtitle}>
          Browse quality control panels that have been shared publicly. View run results and check statuses.
        </p>

        {loading && <p className={styles.muted}>Loading...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && !error && operations.length === 0 && (
          <div className={styles.emptyState}>
            <p>No public quality control panels available yet.</p>
          </div>
        )}

        <div className={styles.grid}>
          {operations.map((op) => (
            <Link key={op.id} href={`/qc/${op.id}`} className={styles.card}>
              <div className={styles.cardHeader}>
                <h2 className={styles.cardName}>{op.name}</h2>
                {op.latest_run && (
                  <span className={op.latest_run.success ? styles.badgePass : styles.badgeFail}>
                    {op.latest_run.success ? 'Passing' : 'Failing'}
                  </span>
                )}
              </div>
              <div className={styles.cardMeta}>
                <span>by {op.owner}</span>
                <span>{op.function_count} check{op.function_count !== 1 ? 's' : ''}</span>
              </div>
              {op.latest_run ? (
                <p className={styles.cardRunInfo}>
                  Last run: {new Date(op.latest_run.created_at).toLocaleString()} — {op.latest_run.row_count} rows
                </p>
              ) : (
                <p className={styles.cardRunInfo}>No runs yet</p>
              )}
            </Link>
          ))}
        </div>
      </main>
    </>
  );
}
