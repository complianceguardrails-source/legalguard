// Client-side port of ingestion/tagger.py's keyword-overlap matcher, so a
// user adding their own use case gets candidate regulations *immediately*,
// without a round trip to the Python ingestion service (which only runs
// server-side, on a schedule). Same algorithm, same honesty caveat: this is
// coarse Jaccard overlap on tokenized keywords, not semantic understanding.
// Treat results as candidates for the user to confirm on the Impact Diff
// screen, not an auto-approved compliance determination.

const STOPWORDS = new Set([
  "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
  "shall", "must", "is", "are", "be", "this", "that", "as", "by", "at",
]);

function tokenize(text) {
  const words = (text || "").toLowerCase().match(/[a-z]{3,}/g) || [];
  return new Set(words.filter((w) => !STOPWORDS.has(w)));
}

function jaccard(setA, setB) {
  if (setA.size === 0 || setB.size === 0) return 0;
  let intersectionSize = 0;
  for (const item of setA) {
    if (setB.has(item)) intersectionSize++;
  }
  const unionSize = setA.size + setB.size - intersectionSize;
  return unionSize === 0 ? 0 : intersectionSize / unionSize;
}

/**
 * @param {{name: string, description?: string, modality?: string, parent_sector?: string}} useCase
 * @param {Array<{reg_id: string, official_title: string, statutory_text?: string, jurisdiction: string, issuing_body: string}>} regulations
 * @param {{topK?: number, minScore?: number}} [options]
 * @returns {Array<{reg_id: string, official_title: string, jurisdiction: string, issuing_body: string, score: number}>}
 */
export function matchRegulationsForUseCase(useCase, regulations, { topK = 5, minScore = 0.04 } = {}) {
  const useCaseText = [useCase.name, useCase.description, useCase.modality, useCase.parent_sector]
    .filter(Boolean)
    .join(" ");
  const useCaseTokens = tokenize(useCaseText);
  if (useCaseTokens.size === 0) return [];

  const scored = regulations
    .map((reg) => {
      const regText = [reg.official_title, reg.statutory_text].filter(Boolean).join(" ");
      const score = jaccard(useCaseTokens, tokenize(regText));
      return { ...reg, score: Math.round(score * 10000) / 10000 };
    })
    .filter((r) => r.score >= minScore)
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, topK);
}
