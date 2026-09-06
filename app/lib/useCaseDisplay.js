// Shared display metadata for a use case's modality and risk_tier -- used by
// KnowledgeBaseScreen.js (the full knowledge base) and ImpactDiffScreen.js
// (the use-case-centric Audit view) so both surfaces render the same icons
// and severity colors instead of drifting apart.
import { Mic, Eye, FileText, Database, Users } from "lucide-react-native";
import { colors } from "../theme";

export const MODALITY_ICON = {
  voice_agentic: Mic,
  vision: Eye,
  rag_document: FileText,
  structured: Database,
  multi_agent: Users,
};

// Loosely follows the EU AI Act's severity gradient (prohibited > high_risk >
// limited_risk > minimal_risk) so the pill color itself communicates how
// serious risk_tier_classifier.py's guess is, not just its label text.
// 'unclassified' gets the same neutral treatment RegulationCard.js gives an
// unverified source -- "not yet known", not "risky".
export const RISK_TIER_STYLE = {
  prohibited: { color: colors.danger, background: "#EF476F26" },
  high_risk: { color: "#F97316", background: "#F9731622" },
  limited_risk: { color: colors.warning, background: "#FFD16630" },
  minimal_risk: { color: colors.success, background: "#06D6A022" },
  unclassified: { color: colors.textMuted, background: "#64748B1F" },
};
