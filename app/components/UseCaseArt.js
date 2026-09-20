// Procedural card art: drawn from the row itself, never fetched or stored.
// The use case's name seeds a PRNG, its first category sets the tone, its
// modality picks the motif -- a grid for tabular systems, document lines
// for RAG, a node network for multi-agent, rings for voice, lenses for
// vision -- and its risk tier sets density. Same row, same picture, every
// time, on every device. No image files, nothing to host, nothing to pay
// for, and 1,438 cards that share one palette by construction.

import React, { useMemo } from "react";
import Svg, { Rect, Circle, Line, Path, Defs, LinearGradient, Stop } from "react-native-svg";

import { useCaseTone } from "../lib/categories";

// FNV-1a over the name, then xorshift32. Small, deterministic, and enough
// variety that no two cards in a deck look alike.
function seedFrom(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function makeRng(seed) {
  let s = seed || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
}

function towardWhite(hex, amount) {
  const n = parseInt(hex.slice(1), 16);
  const f = (c) => Math.round(c + (255 - c) * amount);
  return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`;
}

const DENSITY = { prohibited: 1.0, high_risk: 0.85, limited_risk: 0.6, minimal_risk: 0.42, unclassified: 0.55 };

// Motif occupies the top portion; the card's text sits below it.
function buildShapes(useCase, W, H) {
  const tone = useCaseTone(useCase);
  const rng = makeRng(seedFrom(useCase.name || ""));
  const density = DENSITY[useCase.risk_tier] ?? 0.55;
  const inks = [towardWhite(tone, 0.22), towardWhite(tone, 0.45), "rgba(255,255,255,0.9)"];
  const ink = () => inks[Math.floor(rng() * inks.length)];
  const area = H * 0.62;
  const shapes = [];
  let k = 0;

  switch (useCase.modality) {
    case "rag_document": {
      const rows = 7 + Math.floor(density * 6);
      const lh = area / rows;
      for (let i = 0; i < rows; i++) {
        const w = W * (0.3 + rng() * 0.62);
        const x = rng() < 0.15 ? W - w - 14 : 14;
        shapes.push(<Rect key={k++} x={x} y={12 + i * lh} width={w} height={Math.max(4, lh * 0.42)} rx={3} fill={ink()} opacity={0.5 + rng() * 0.45} />);
      }
      break;
    }
    case "multi_agent": {
      const n = 5 + Math.floor(density * 6);
      const pts = [];
      for (let i = 0; i < n; i++) pts.push([16 + rng() * (W - 32), 14 + rng() * (area - 28)]);
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          if (rng() < 0.32) {
            shapes.push(<Line key={k++} x1={pts[i][0]} y1={pts[i][1]} x2={pts[j][0]} y2={pts[j][1]} stroke="rgba(255,255,255,0.55)" strokeWidth={1.4} />);
          }
        }
      }
      for (const [x, y] of pts) shapes.push(<Circle key={k++} cx={x} cy={y} r={5 + rng() * 7} fill={ink()} opacity={0.95} />);
      break;
    }
    case "voice_agentic": {
      const cx = W * (0.3 + rng() * 0.4);
      const cy = area * 0.55;
      const n = 5 + Math.floor(density * 5);
      for (let i = 1; i <= n; i++) {
        const r = i * (area / (n * 2));
        const a0 = rng() * Math.PI * 2;
        const a1 = a0 + Math.PI * (0.5 + rng());
        const large = a1 - a0 > Math.PI ? 1 : 0;
        const d = `M ${cx + r * Math.cos(a0)} ${cy + r * Math.sin(a0)} A ${r} ${r} 0 ${large} 1 ${cx + r * Math.cos(a1)} ${cy + r * Math.sin(a1)}`;
        shapes.push(<Path key={k++} d={d} stroke={ink()} strokeWidth={3} strokeLinecap="round" fill="none" opacity={0.5 + rng() * 0.45} />);
      }
      break;
    }
    case "vision": {
      const n = 3 + Math.floor(density * 5);
      for (let i = 0; i < n; i++) {
        shapes.push(<Circle key={k++} cx={20 + rng() * (W - 40)} cy={16 + rng() * (area - 32)} r={18 + rng() * 42} fill={ink()} opacity={0.28 + rng() * 0.35} />);
      }
      break;
    }
    case "structured":
    default: {
      const n = 6;
      const cell = W / n;
      const pad = cell * 0.16;
      const rows = Math.floor(area / cell);
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < n; x++) {
          if (rng() > density) continue;
          shapes.push(<Rect key={k++} x={x * cell + pad} y={y * cell + pad + 8} width={cell - pad * 2} height={cell - pad * 2} rx={4} fill={ink()} opacity={0.55 + rng() * 0.45} />);
        }
      }
    }
  }
  return { tone, shapes };
}

/**
 * @param {object} props.useCase - a banking_use_cases row
 * @param {number} props.width
 * @param {number} props.height
 */
export default function UseCaseArt({ useCase, width, height, style, scrim = true }) {
  const { tone, shapes } = useMemo(() => buildShapes(useCase, width, height), [useCase, width, height]);
  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={style}>
      <Defs>
        <LinearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0.38" stopColor="#000000" stopOpacity="0" />
          <Stop offset="1" stopColor="#000000" stopOpacity="0.38" />
        </LinearGradient>
      </Defs>
      <Rect x={0} y={0} width={width} height={height} fill={tone} />
      {shapes}
      {scrim && <Rect x={0} y={0} width={width} height={height} fill="url(#scrim)" />}
    </Svg>
  );
}
