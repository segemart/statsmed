'use client';

import { useEffect, useState } from 'react';
import type { AcceptanceBarChartData } from '../lib/api';
import styles from './AcceptanceBar.module.css';

interface AcceptanceBarProps {
  data: AcceptanceBarChartData;
}

export default function AcceptanceBar({ data }: AcceptanceBarProps) {
  const { accepted, rejected, total, accepted_pct, rejected_pct } = data;
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const accWidth = animated ? accepted_pct : 0;
  const rejWidth = animated ? rejected_pct : 0;

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.total}>n = {total}</span>
      </div>

      <div className={styles.track}>
        {accepted_pct > 0 && (
          <div
            className={styles.accepted}
            style={{ width: `${accWidth}%` }}
          >
            {accepted_pct >= 12 && (
              <span className={styles.label}>
                {accepted} ({accepted_pct}%)
              </span>
            )}
          </div>
        )}
        {rejected_pct > 0 && (
          <div
            className={styles.rejected}
            style={{ width: `${rejWidth}%` }}
          >
            {rejected_pct >= 12 && (
              <span className={styles.label}>
                {rejected} ({rejected_pct}%)
              </span>
            )}
          </div>
        )}
      </div>

      <div className={styles.legend}>
        <span className={styles.legendAccepted}>
          <span className={styles.legendDot} data-kind="accepted" />
          Accepted: {accepted} ({accepted_pct}%)
        </span>
        <span className={styles.legendRejected}>
          <span className={styles.legendDot} data-kind="rejected" />
          Rejected: {rejected} ({rejected_pct}%)
        </span>
      </div>
    </div>
  );
}
