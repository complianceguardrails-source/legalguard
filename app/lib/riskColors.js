// One colour per risk family, used by the Guardrails wheel and the
// Trending chart so a colour means the same thing wherever it appears.
//
// Seven distinct hues -- blue, teal, orange, violet, slate, magenta,
// green -- rather than the several blues this started as: on a chart with
// seven lines, hue is the only thing telling them apart. Every tone clears
// 4.5:1 against white text, which the wheel needs for its family labels.
export const FAMILY_TONE = {
  systemic: "#2547C7",
  model: "#0E7C70",
  cyber: "#C2410C",
  legal: "#7C3AED",
  vendor: "#475569",
  ethical: "#BE185D",
  environmental: "#15803D",
};

// Short names for the wheel's inner ring, where a full label never fits.
export const FAMILY_SHORT = {
  systemic: "Systemic",
  model: "Model",
  cyber: "Cyber",
  legal: "Legal",
  vendor: "Vendor",
  ethical: "Ethical",
  environmental: "Environment",
};

// A second encoding for line charts: where two families have the same
// counts their curves sit exactly on top of each other and colour alone
// cannot separate them, so each family also has its own dash pattern.
// It doubles as the colour-blind fallback.
export const FAMILY_DASH = {
  systemic: undefined,
  model: "7,4",
  cyber: "2,4",
  legal: "11,4",
  vendor: "7,4,2,4",
  ethical: "3,3",
  environmental: "14,5",
};

/**
 * A smooth SVG path through the given points (Catmull-Rom converted to
 * cubic Béziers). Straight polylines between weekly counts read as sharp
 * spikes; this keeps the same values but draws the line as a curve.
 * `tension` 0 is a straight line, 1 is very loose; 0.5 is the usual.
 */
export function smoothPath(points, tension = 0.5) {
  if (points.length < 2) return "";
  if (points.length === 2) return `M ${points[0][0]} ${points[0][1]} L ${points[1][0]} ${points[1][1]}`;
  const k = tension / 6;
  let d = `M ${points[0][0]} ${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) * k;
    const c1y = p1[1] + (p2[1] - p0[1]) * k;
    const c2x = p2[0] - (p3[0] - p1[0]) * k;
    const c2y = p2[1] - (p3[1] - p1[1]) * k;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2[0]} ${p2[1]}`;
  }
  return d;
}
