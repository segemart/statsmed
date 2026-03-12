'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { getPublicQCOperation, type PublicQCOperationDetail } from '../../lib/api';
import styles from '../PublicQC.module.css';
import logoImg from '../../../Icon/NewIcon.png';

export default function PublicQCDetailPage() {
  const params = useParams();
  const operationId = Number(params.id);
  const [operation, setOperation] = useState<PublicQCOperationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!operationId) return;
    getPublicQCOperation(operationId)
      .then(setOperation)
      .catch(() => setError('Operation not found or not public.'))
      .finally(() => setLoading(false));
  }, [operationId]);

  const run = operation?.latest_run;

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
        <Link href="/qc" className={styles.backLink}>
          &larr; All public panels
        </Link>

        {loading && <p className={styles.muted}>Loading...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {operation && (
          <>
            <div className={styles.detailHeader}>
              <h1 className={styles.detailName}>{operation.name}</h1>
              <div className={styles.detailMeta}>
                <span>by {operation.owner}</span>
                <span>Created {new Date(operation.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {run ? (
              <section className={styles.section}>
                <div className={styles.runHeader}>
                  <span
                    className={styles.runStatus}
                    style={{ color: run.success ? 'var(--accent-green)' : 'var(--accent-red)' }}
                  >
                    {run.success ? 'All checks passed' : 'Some checks failed'}
                  </span>
                  <span className={styles.runMeta}>
                    {run.row_count} rows &mdash; {new Date(run.created_at).toLocaleString()}
                  </span>
                </div>
                <ul className={styles.resultList}>
                  {run.results.map((r, i) => (
                    <li key={i} className={styles.resultItem}>
                      <span
                        className={styles.resultIcon}
                        style={{ color: r.passed ? 'var(--accent-green)' : 'var(--accent-red)' }}
                      >
                        {r.passed ? '\u2713' : '\u2717'}
                      </span>
                      <span className={styles.resultName}>{r.name}</span>
                      <span>{r.message}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <section className={styles.section}>
                <p className={styles.muted}>No results available yet.</p>
              </section>
            )}
          </>
        )}
      </main>
    </>
  );
}
