'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { LaneyPChartPoint } from '../lib/api';
import styles from './LaneyPChart.module.css';

interface LaneyPChartProps {
  points: LaneyPChartPoint[];
  pbar: number;
  sigma_z: number;
  k: number;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function formatTooltipDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function LaneyPChart({ points, pbar, sigma_z, k }: LaneyPChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; point: LaneyPChartPoint } | null>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setAnimated(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const margin = { top: 20, right: 20, bottom: 44, left: 52 };
  const width = 700;
  const height = 320;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const { xScale, yScale, linePath, uclPath, lclPath, centerY, xTicks, yTicks } = useMemo(() => {
    if (points.length === 0) {
      return { xScale: () => 0, yScale: () => 0, linePath: '', uclPath: '', lclPath: '', centerY: 0, xTicks: [] as { label: string; x: number }[], yTicks: [] as number[] };
    }

    const times = points.map((pt) => new Date(pt.date).getTime());
    const minT = Math.min(...times);
    const maxT = Math.max(...times);
    const rangeT = maxT - minT || 1;

    const allValues = points.flatMap((pt) => [pt.p, ...(pt.lcl != null ? [pt.lcl] : []), ...(pt.ucl != null ? [pt.ucl] : [])]);
    const minV = Math.min(...allValues, pbar);
    const maxV = Math.max(...allValues, pbar);
    const pad = Math.max((maxV - minV) * 0.15, 0.02);
    const yMin = Math.max(0, minV - pad);
    const yMax = Math.min(1, maxV + pad);
    const yRange = yMax - yMin || 0.01;

    const xScale = (t: number) => ((t - minT) / rangeT) * innerW;
    const yScale = (v: number) => innerH - ((v - yMin) / yRange) * innerH;

    const linePath = points
      .map((pt, i) => `${i === 0 ? 'M' : 'L'}${xScale(times[i])},${yScale(pt.p)}`)
      .join(' ');

    const buildLimitPath = (key: 'ucl' | 'lcl') => {
      let started = false;
      return points
        .map((pt, i) => {
          const v = pt[key];
          if (v == null) return '';
          const cmd = started ? 'L' : 'M';
          started = true;
          return `${cmd}${xScale(times[i])},${yScale(v)}`;
        })
        .join(' ');
    };
    const uclPath = buildLimitPath('ucl');
    const lclPath = buildLimitPath('lcl');

    const centerY = yScale(pbar);

    const niceStep = (range: number, targetTicks: number) => {
      const rough = range / targetTicks;
      const mag = Math.pow(10, Math.floor(Math.log10(rough)));
      const norm = rough / mag;
      const step = norm < 1.5 ? mag : norm < 3.5 ? 2 * mag : norm < 7.5 ? 5 * mag : 10 * mag;
      return step;
    };

    const step = niceStep(yRange, 5);
    const yTicks: number[] = [];
    let tick = Math.ceil(yMin / step) * step;
    while (tick <= yMax + step * 0.01) {
      yTicks.push(tick);
      tick += step;
    }

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

    return { xScale, yScale, linePath, uclPath, lclPath, centerY, xTicks, yTicks };
  }, [points, pbar, innerW, innerH]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || points.length === 0) return;
    const rect = svgRef.current.getBoundingClientRect();
    const svgX = (e.clientX - rect.left) * (width / rect.width);
    const mx = svgX - margin.left;
    const times = points.map((pt) => new Date(pt.date).getTime());
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

    const allValues = points.flatMap((pt) => [pt.p, ...(pt.lcl != null ? [pt.lcl] : []), ...(pt.ucl != null ? [pt.ucl] : [])]);
    const minV = Math.min(...allValues, pbar);
    const maxV = Math.max(...allValues, pbar);
    const pad = Math.max((maxV - minV) * 0.15, 0.02);
    const yMin = Math.max(0, minV - pad);
    const yMax = Math.min(1, maxV + pad);
    const yRange = yMax - yMin || 0.01;

    const px = ((times[closest] - minT) / rangeT) * innerW + margin.left;
    const py = innerH - ((points[closest].p - yMin) / yRange) * innerH + margin.top;
    setTooltip({ x: px, y: py, point: points[closest] });
  };

  if (points.length === 0) {
    return (
      <div className={styles.wrapper}>
        <p className={styles.empty}>
          Not enough data for a Laney p&prime; chart yet. At least 2 runs with an Acceptance/Rejection bar are required.
        </p>
      </div>
    );
  }

  const oocCount = points.filter((pt) => pt.out_of_control).length;

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>Laney p&prime; Chart</h3>
      <div className={styles.stats}>
        <span className={styles.stat}>
          p&#772; = {(pbar * 100).toFixed(1)}%
        </span>
        <span className={styles.stat}>
          &sigma;<sub>z</sub> = {sigma_z.toFixed(3)}
        </span>
        <span className={styles.stat}>
          k = {k}
        </span>
        {oocCount > 0 && (
          <span className={`${styles.stat} ${styles.statAlert}`}>
            {oocCount} out of control
          </span>
        )}
      </div>
      <div className={styles.chartContainer}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className={styles.svg}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
        >
          <g transform={`translate(${margin.left},${margin.top})`}>
            {yTicks.map((v) => (
              <g key={v}>
                <line x1={0} y1={yScale(v)} x2={innerW} y2={yScale(v)} className={styles.gridLine} />
                <text x={-10} y={yScale(v)} className={styles.yLabel}>
                  {(v * 100).toFixed(0)}%
                </text>
              </g>
            ))}

            {xTicks.map((t, i) => (
              <text key={i} x={t.x} y={innerH + 28} className={styles.xLabel}>
                {t.label}
              </text>
            ))}

            {/* Center line (pbar) */}
            <line x1={0} y1={centerY} x2={innerW} y2={centerY} className={styles.centerLine} />
            <text x={innerW + 4} y={centerY} className={styles.limitLabel}>p&#772;</text>

            {/* UCL */}
            <path d={uclPath} className={`${styles.limitLine} ${styles.uclLine} ${animated ? styles.limitVisible : ''}`} />

            {/* LCL */}
            <path d={lclPath} className={`${styles.limitLine} ${styles.lclLine} ${animated ? styles.limitVisible : ''}`} />

            {/* Observed proportion line */}
            <path d={linePath} className={`${styles.dataLine} ${animated ? styles.dataLineVisible : ''}`} />

            {/* Data points */}
            {points.map((pt, i) => (
              <circle
                key={i}
                cx={xScale(new Date(pt.date).getTime())}
                cy={yScale(pt.p)}
                r={points.length <= 30 ? 4.5 : 3}
                className={`${pt.out_of_control ? styles.dotOoc : styles.dot} ${animated ? styles.dotVisible : ''}`}
              />
            ))}
          </g>

          {tooltip && (
            <g>
              <line
                x1={tooltip.x}
                y1={margin.top}
                x2={tooltip.x}
                y2={height - margin.bottom}
                className={styles.crosshair}
              />
              <circle
                cx={tooltip.x}
                cy={tooltip.y}
                r={6}
                className={tooltip.point.out_of_control ? styles.tooltipDotOoc : styles.tooltipDot}
              />
            </g>
          )}
        </svg>

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
              <span className={tooltip.point.out_of_control ? styles.tooltipOoc : styles.tooltipNormal}>
                {(tooltip.point.p * 100).toFixed(1)}%
              </span>
            </div>
            <div className={styles.tooltipMeta}>n = {tooltip.point.n}</div>
            {tooltip.point.lcl != null && tooltip.point.ucl != null && (
              <div className={styles.tooltipMeta}>
                LCL {(tooltip.point.lcl * 100).toFixed(1)}% &ndash; UCL {(tooltip.point.ucl * 100).toFixed(1)}%
              </div>
            )}
            {tooltip.point.out_of_control && (
              <div className={styles.tooltipFlag}>out of control</div>
            )}
          </div>
        )}
      </div>

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.legendLine} data-kind="data" /> Observed p
        </span>
        <span className={styles.legendItem}>
          <span className={styles.legendLine} data-kind="center" /> p&#772; (center)
        </span>
        <span className={styles.legendItem}>
          <span className={styles.legendLine} data-kind="limits" /> UCL / LCL
        </span>
        {oocCount > 0 && (
          <span className={styles.legendItem}>
            <span className={styles.legendDotOoc} /> Out of control
          </span>
        )}
      </div>
    </div>
  );
}
