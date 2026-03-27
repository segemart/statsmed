'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import {
  getPublicQCOperation,
  type PublicQCOperationDetail,
  type AcceptanceHistoryChartData,
  type LaneyPChartData,
} from '../../lib/api';
import AcceptanceBar from '../../components/AcceptanceBar';
import AcceptanceChart from '../../components/AcceptanceChart';
import LaneyPChart from '../../components/LaneyPChart';
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
                      <div className={styles.resultItemHeader}>
                        <span
                          className={styles.resultIcon}
                          style={{ color: r.passed ? 'var(--accent-green)' : 'var(--accent-red)' }}
                        >
                          {r.passed ? '\u2713' : '\u2717'}
                        </span>
                        <span className={styles.resultName}>{r.name}</span>
                      </div>
                      <pre className={styles.resultMessage}>{r.message}</pre>
                      {r.chart_data?.type === 'acceptance_bar' && (
                        <AcceptanceBar data={r.chart_data} />
                      )}
                      {r.chart_data?.type === 'acceptance_history' && (r.chart_data as AcceptanceHistoryChartData).points.length > 1 && (
                        <AcceptanceChart points={(r.chart_data as AcceptanceHistoryChartData).points} />
                      )}
                      {r.chart_data?.type === 'laney_p_chart' && (r.chart_data as LaneyPChartData).points.length >= 2 && (
                        <LaneyPChart
                          points={(r.chart_data as LaneyPChartData).points}
                          pbar={(r.chart_data as LaneyPChartData).pbar}
                          sigma_z={(r.chart_data as LaneyPChartData).sigma_z}
                          k={(r.chart_data as LaneyPChartData).k}
                        />
                      )}
                      {r.figure && !r.chart_data && (
                        <img
                          className={styles.resultFigure}
                          src={`data:image/png;base64,${r.figure}`}
                          alt={r.name}
                        />
                      )}
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
