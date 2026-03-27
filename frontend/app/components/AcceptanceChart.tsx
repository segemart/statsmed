'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { AcceptanceHistoryPoint } from '../lib/api';
import styles from './AcceptanceChart.module.css';

interface AcceptanceChartProps {
  points: AcceptanceHistoryPoint[];
}

interface Tick {
  label: string;
  x: number;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function formatTooltipDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function AcceptanceChart({ points }: AcceptanceChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; point: AcceptanceHistoryPoint } | null>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const margin = { top: 20, right: 20, bottom: 44, left: 52 };
  const width = 700;
  const height = 300;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const { xScale, yScale, linePath, areaPath, xTicks, yTicks } = useMemo(() => {
    if (points.length === 0) {
      return { xScale: () => 0, yScale: () => 0, linePath: '', areaPath: '', xTicks: [], yTicks: [] };
    }

    const times = points.map((p) => new Date(p.date).getTime());
    const minT = Math.min(...times);
    const maxT = Math.max(...times);
    const rangeT = maxT - minT || 1;

    const xScale = (t: number) => ((t - minT) / rangeT) * innerW;
    const yScale = (v: number) => innerH - (v / 100) * innerH;

    const lineCoords = points.map((p, i) => {
      const x = xScale(times[i]);
      const y = yScale(p.accepted_pct);
      return `${i === 0 ? 'M' : 'L'}${x},${y}`;
    });
    const linePath = lineCoords.join(' ');

    const areaPath =
      lineCoords.join(' ') +
      ` L${xScale(times[times.length - 1])},${innerH} L${xScale(times[0])},${innerH} Z`;

    const yTicks = [0, 25, 50, 75, 100];

    const minLabelGap = 90;
    const xTicks: Tick[] = [{ label: formatDate(points[0].date), x: xScale(times[0]) }];
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

    return { xScale, yScale, linePath, areaPath, xTicks, yTicks };
  }, [points, innerW, innerH]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || points.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mx = e.clientX - rect.left - margin.left;
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
    const py = (innerH - (points[closest].accepted_pct / 100) * innerH) + margin.top;
    setTooltip({ x: px, y: py, point: points[closest] });
  };

  if (points.length === 0) {
    return (
      <div className={styles.wrapper}>
        <p className={styles.empty}>No acceptance history data available yet.</p>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>Acceptance Rate Over Time</h3>
      <div className={styles.chartContainer}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className={styles.svg}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
        >
          <g transform={`translate(${margin.left},${margin.top})`}>
            {/* Y grid lines + labels */}
            {yTicks.map((v) => (
              <g key={v}>
                <line
                  x1={0}
                  y1={yScale(v)}
                  x2={innerW}
                  y2={yScale(v)}
                  className={styles.gridLine}
                />
                <text x={-10} y={yScale(v)} className={styles.yLabel}>
                  {v}%
                </text>
              </g>
            ))}

            {/* X labels */}
            {xTicks.map((t, i) => (
              <text key={i} x={t.x} y={innerH + 28} className={styles.xLabel}>
                {t.label}
              </text>
            ))}

            {/* Area fill */}
            <path
              d={areaPath}
              className={`${styles.area} ${animated ? styles.areaVisible : ''}`}
            />

            {/* Line */}
            <path
              d={linePath}
              className={`${styles.line} ${animated ? styles.lineVisible : ''}`}
            />

            {/* Data points */}
            {points.map((p, i) => (
              <circle
                key={i}
                cx={xScale(new Date(p.date).getTime())}
                cy={yScale(p.accepted_pct)}
                r={points.length <= 30 ? 4 : 2.5}
                className={`${styles.dot} ${animated ? styles.dotVisible : ''}`}
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
              <circle cx={tooltip.x} cy={tooltip.y} r={6} className={styles.tooltipDot} />
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
              <span className={styles.tooltipAccepted}>{tooltip.point.accepted_pct}%</span> accepted
            </div>
            <div className={styles.tooltipMeta}>n = {tooltip.point.total}</div>
          </div>
        )}
      </div>
    </div>
  );
}
