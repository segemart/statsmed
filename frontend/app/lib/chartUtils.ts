/**
 * Logarithmic-density index selection for chart point thinning.
 *
 * When a chart has more points than `maxVisible`, this returns a Set of
 * indices to keep.  Recent points (high indices) are kept at full density
 * while older points are progressively thinned — the spacing follows a
 * power-curve so the visual effect resembles a soft log-scale compression
 * of the past.
 *
 * Points whose indices appear in `mustKeep` (e.g. out-of-control flags)
 * are always retained regardless of the budget.
 */
export function logDensityIndices(
  total: number,
  maxVisible: number,
  mustKeep?: ReadonlySet<number>,
): Set<number> {
  if (total <= maxVisible) {
    const all = new Set<number>();
    for (let i = 0; i < total; i++) all.add(i);
    return all;
  }

  const indices = new Set<number>();

  if (mustKeep) {
    mustKeep.forEach((idx) => indices.add(idx));
  }

  indices.add(0);
  indices.add(total - 1);

  const budget = Math.max(maxVisible - indices.size, 0);
  for (let i = 0; i < budget; i++) {
    const t = budget > 1 ? i / (budget - 1) : 1;
    // Power-curve: exponent < 2 keeps it "slightly log", not too aggressive
    const curved = Math.pow(t, 1.7);
    indices.add(Math.round(curved * (total - 1)));
  }

  return indices;
}

export const MAX_CHART_DOTS = 100;
