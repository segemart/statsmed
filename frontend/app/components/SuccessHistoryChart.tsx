'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { SuccessHistoryPoint } from '../lib/api';
import styles from './AcceptanceChart.module.css';

interface SuccessHistoryChartProps {
  points: SuccessHistoryPoint[];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function formatTooltipDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function SuccessHistoryChart({ points }: SuccessHistoryChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; point: SuccessHistoryPoint } | null>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const margin = { top: 20, right: 44, bottom: 44, left: 52 };
  const width = 700;
  const height = 200;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const { xScale, yScale, xTicks } = useMemo(() => {
    if (points.length === 0) {
      return { xScale: () => 0, yScale: () => 0, xTicks: [] as { label: string; x: number }[] };
    }

    const times = points.map((p) => new Date(p.date).getTime());
    const minT = Math.min(...times);
    const maxT = Math.max(...times);
    const rangeT = maxT - minT || 1;

    const xScale = (t: number) => ((t - minT) / rangeT) * innerW;
    const yScale = (v: number) => innerH - v * innerH;

    const minLabelGap = 90;
    const xTicks: { label: string; x: number }[] = [{ label: formatDate(points[0].date), x: xScale(times[0]) }];
    for (let i = 1; i < points.length; i++) {
      const px = xScale(times[i]);
      if (px - xTicks[xTicks.length - 1].x >= minLabelGap) {
        xTicks.push({ label: formatDate(points[i].date), x: px });
      }
    }
    const lastIdx = points.length - 1;
    if (lastIdx > 0) {
      const lastX = xScale(times[lastIdx]);
      if (lastX - xTicks[xTicks.length - 1].x >= minLabelGap * 0.5) {
        xTicks.push({ label: formatDate(points[lastIdx].date), x: lastX });
      }
    }

    return { xScale, yScale, xTicks };
  }, [points, innerW, innerH]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || points.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const svgX = (e.clientX - rect.left) * (width / rect.width);
    const mx = svgX - margin.left;
    const times = points.map((p) => new Date(p.date).getTime());
    const minT = Math.min(...times);
    const maxT = Math.max(...times);
    const rangeT = maxT - minT || 1;

    let closest = 0;
    let closestDist = Infinity;
    for (let i = 0; i < points.length; i++) {
      const px = ((times[i] - minT) / rangeT) * innerW;
      const dist = Math.abs(px - mx);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    }

    const px = ((times[closest] - minT) / rangeT) * innerW + margin.left;
    const py = (innerH - points[closest].value * innerH) + margin.top;
    setTooltip({ x: px, y: py, point: points[closest] });
  };

  if (points.length === 0) {
    return (
      <div className={styles.wrapper}>
        <p className={styles.empty}>No success/failure history data available yet.</p>
      </div>
    );
  }

  const successes = points.filter((p) => p.value === 1).length;
  const failures = points.length - successes;
  const rate = ((successes / points.length) * 100).toFixed(1);

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>Success / Failure Over Time</h3>
      <p style={{ fontSize: '0.82rem', color: 'var(--muted)', margin: '0 0 4px' }}>
        {successes} success, {failures} failure ({rate}% success rate)
      </p>
      <div className={styles.chartContainer}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className={styles.svg}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
        >
          <g transform={`translate(${margin.left},${margin.top})`}>
            {/* Y labels */}
            <text x={-10} y={yScale(1)} style={{ fontSize: 11, fill: 'var(--muted)', textAnchor: 'end', dominantBaseline: 'middle' }}>
              Success
            </text>
            <text x={-10} y={yScale(0)} style={{ fontSize: 11, fill: 'var(--muted)', textAnchor: 'end', dominantBaseline: 'middle' }}>
              Failure
            </text>

            {/* Grid lines */}
            <line x1={0} y1={yScale(1)} x2={innerW} y2={yScale(1)} className={styles.gridLine} />
            <line x1={0} y1={yScale(0)} x2={innerW} y2={yScale(0)} className={styles.gridLine} />

            {/* X labels */}
            {xTicks.map((t, i) => (
              <text key={i} x={t.x} y={innerH + 28} className={styles.xLabel}>
                {t.label}
              </text>
            ))}

            {/* Data points */}
            {points.map((p, i) => (
              <circle
                key={i}
                cx={xScale(new Date(p.date).getTime())}
                cy={yScale(p.value)}
                r={points.length <= 30 ? 6 : 4}
                fill={p.value === 1 ? '#22c55e' : '#ef4444'}
                opacity={animated ? 1 : 0}
                style={{ transition: `opacity 0.4s ease ${i * 0.03}s` }}
              />
            ))}
          </g>

          {/* Tooltip crosshair */}
          {tooltip && (
            <g>
              <line
                x1={tooltip.x}
                y1={margin.top}
                x2={tooltip.x}
                y2={height - margin.bottom}
                className={styles.crosshair}
              />
              <circle cx={tooltip.x} cy={tooltip.y} r={8}
                fill={tooltip.point.value === 1 ? '#22c55e' : '#ef4444'}
                opacity={0.7}
              />
            </g>
          )}
        </svg>

        {/* Tooltip card */}
        {tooltip && (
          <div
            className={styles.tooltipCard}
            style={{
              left: `${(tooltip.x / width) * 100}%`,
              top: `${(tooltip.y / height) * 100}%`,
            }}
          >
            <div className={styles.tooltipDate}>{formatTooltipDate(tooltip.point.date)}</div>
            <div className={styles.tooltipValue}>
              <span style={{ color: tooltip.point.value === 1 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                {tooltip.point.value === 1 ? 'Success' : 'Failure'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
