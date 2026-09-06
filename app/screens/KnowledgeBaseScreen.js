import React, { useEffect, useState, useMemo } from "react";
import { View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity, Modal, ScrollView, Alert } from "react-native";
import { Search, Plus, X, Database, Cpu } from "lucide-react-native";

import { colors, type, radius } from "../theme";
import { fetchUseCases, fetchRegulations, submitUseCase } from "../lib/api";
import { getGitHubCredentials } from "../lib/auth";
import { matchRegulationsForUseCase } from "../lib/tagger";
import { deriveRiskTier } from "../lib/riskTierHeuristic";
import { MODALITY_ICON, RISK_TIER_STYLE } from "../lib/useCaseDisplay";
import MetadataPill from "../components/MetadataPill";

const SECTOR_OPTIONS = [
  "Consumer Finance",
  "Front Office",
  "CIB",
  "Wealth Management",
  "Operations & Risk",
  "Insurance",
  "Climate & Sustainable Finance",
];
const MODALITY_OPTIONS = ["structured", "vision", "voice_agentic", "rag_document", "multi_agent"];
// Plain-language jurisdiction options -- "where does this operate" rather
// than "which regulations apply to you". Codes match specific_regulations'
// informal convention (EU | US | US-CA | UK ...) so a prefix match in
// tagger.js::matchRegulationsForUseCase works directly.
const JURISDICTION_OPTIONS = [
  { code: "US", label: "United States" },
  { code: "EU", label: "European Union" },
  { code: "UK", label: "United Kingdom" },
  { code: "OTHER", label: "Other / Global" },
];

export default function KnowledgeBaseScreen() {
  const [useCases, setUseCases] = useState([]);
  const [regulations, setRegulations] = useState([]);
  const [query, setQuery] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const load = () => {
    fetchUseCases().then(setUseCases);
    fetchRegulations().then(setRegulations);
  };

  useEffect(load, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return useCases;
    return useCases.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.parent_sector?.toLowerCase().includes(q) ||
        u.modality?.toLowerCase().includes(q)
    );
  }, [useCases, query]);

  return (
    <View style={styles.container}>
      <View style={styles.searchBar}>
        <Search size={16} color={colors.textMuted} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search use cases (e.g. 'voice', 'green mortgage')"
          placeholderTextColor={colors.textMuted}
          value={query}
          onChangeText={setQuery}
        />
        <TouchableOpacity style={styles.addButton} onPress={() => setModalOpen(true)}>
          <Plus size={16} color={colors.primary} />
        </TouchableOpacity>
      </View>
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 20, paddingTop: 12 }}
        renderItem={({ item }) => <UseCaseCard useCase={item} />}
        ListEmptyComponent={<Text style={styles.emptyText}>No use cases match "{query}".</Text>}
      />

      <AddUseCaseModal
        visible={modalOpen}
        onClose={() => setModalOpen(false)}
        regulations={regulations}
        onSubmitted={load}
      />
    </View>
  );
}

function AddUseCaseModal({ visible, onClose, regulations, onSubmitted }) {
  const [name, setName] = useState("");
  const [sector, setSector] = useState(SECTOR_OPTIONS[0]);
  const [modality, setModality] = useState(MODALITY_OPTIONS[0]);
  const [description, setDescription] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [operatingJurisdictions, setOperatingJurisdictions] = useState([]);
  const [affectsIndividual, setAffectsIndividual] = useState(null); // null = not yet answered
  const [automationDegree, setAutomationDegree] = useState(null); // 'full' | 'reviewed'
  const [busy, setBusy] = useState(false);
  const [matches, setMatches] = useState(null);

  const toggleJurisdiction = (code) => {
    setOperatingJurisdictions((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const reset = () => {
    setName("");
    setDescription("");
    setGithubUrl("");
    setSector(SECTOR_OPTIONS[0]);
    setModality(MODALITY_OPTIONS[0]);
    setOperatingJurisdictions([]);
    setAffectsIndividual(null);
    setAutomationDegree(null);
    setMatches(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async () => {
    if (!name.trim()) return Alert.alert("Name required", "Give your use case a short name.");
    if (operatingJurisdictions.length === 0) {
      return Alert.alert("Jurisdiction required", "Select at least one region this system operates in.");
    }
    if (affectsIndividual === null) {
      return Alert.alert("One more question", "Let us know whether this system decides something about a specific person.");
    }
    if (affectsIndividual && automationDegree === null) {
      return Alert.alert("One more question", "Let us know whether a human reviews the outcome before it's acted on.");
    }
    setBusy(true);
    try {
      const { username } = await getGitHubCredentials();
      const riskTier = deriveRiskTier({ affectsIndividual, automationDegree });
      await submitUseCase({
        name: name.trim(),
        parentSector: sector,
        modality,
        description: description.trim(),
        submittedByGithubUsername: username,
        githubReferenceUrl: githubUrl.trim() || null,
        operatingJurisdictions,
        riskTier,
      });

      // Candidate compliance matches, computed locally against whatever
      // regulations are already loaded -- no server round-trip needed.
      const found = matchRegulationsForUseCase(
        { name, description, modality, parent_sector: sector },
        regulations,
        { operatingJurisdictions }
      );
      setMatches(found);
      onSubmitted();
    } catch (err) {
      Alert.alert("Couldn't add use case", err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={handleClose} transparent>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalSheet}>
          <View style={styles.modalHeaderRow}>
            <Text style={styles.modalTitle}>Add your use case</Text>
            <TouchableOpacity onPress={handleClose}>
              <X size={18} color={colors.textMuted} />
            </TouchableOpacity>
          </View>

          {matches === null ? (
            <ScrollView>
              <Text style={styles.fieldLabel}>Name</Text>
              <TextInput
                style={styles.input}
                value={name}
                onChangeText={setName}
                placeholder="e.g. Invoice Factoring Risk Scoring"
                placeholderTextColor={colors.textMuted}
              />

              <Text style={styles.fieldLabel}>Sector</Text>
              <View style={styles.chipRow}>
                {SECTOR_OPTIONS.map((opt) => (
                  <TouchableOpacity
                    key={opt}
                    style={[styles.chip, sector === opt && styles.chipSelected]}
                    onPress={() => setSector(opt)}
                  >
                    <Text style={[styles.chipText, sector === opt && styles.chipTextSelected]}>{opt}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.fieldLabel}>Modality</Text>
              <View style={styles.chipRow}>
                {MODALITY_OPTIONS.map((opt) => (
                  <TouchableOpacity
                    key={opt}
                    style={[styles.chip, modality === opt && styles.chipSelected]}
                    onPress={() => setModality(opt)}
                  >
                    <Text style={[styles.chipText, modality === opt && styles.chipTextSelected]}>
                      {opt.replace("_", " ")}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.fieldLabel}>Description</Text>
              <TextInput
                style={[styles.input, { height: 80, textAlignVertical: "top" }]}
                value={description}
                onChangeText={setDescription}
                placeholder="What does this AI system do, and what data/decisions does it touch?"
                placeholderTextColor={colors.textMuted}
                multiline
              />

              <Text style={styles.fieldLabel}>Where does this operate?</Text>
              <View style={styles.chipRow}>
                {JURISDICTION_OPTIONS.map((opt) => (
                  <TouchableOpacity
                    key={opt.code}
                    style={[styles.chip, operatingJurisdictions.includes(opt.code) && styles.chipSelected]}
                    onPress={() => toggleJurisdiction(opt.code)}
                  >
                    <Text
                      style={[
                        styles.chipText,
                        operatingJurisdictions.includes(opt.code) && styles.chipTextSelected,
                      ]}
                    >
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.fieldLabel}>Does it decide something about a person or people?</Text>
              <View style={styles.chipRow}>
                <TouchableOpacity
                  style={[styles.chip, affectsIndividual === true && styles.chipSelected]}
                  onPress={() => setAffectsIndividual(true)}
                >
                  <Text style={[styles.chipText, affectsIndividual === true && styles.chipTextSelected]}>Yes</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.chip, affectsIndividual === false && styles.chipSelected]}
                  onPress={() => {
                    setAffectsIndividual(false);
                    setAutomationDegree(null);
                  }}
                >
                  <Text style={[styles.chipText, affectsIndividual === false && styles.chipTextSelected]}>
                    No, internal processes
                  </Text>
                </TouchableOpacity>
              </View>

              {affectsIndividual === true && (
                <>
                  <Text style={styles.fieldLabel}>Does a human review before action?</Text>
                  <View style={styles.chipRow}>
                    <TouchableOpacity
                      style={[styles.chip, automationDegree === "full" && styles.chipSelected]}
                      onPress={() => setAutomationDegree("full")}
                    >
                      <Text style={[styles.chipText, automationDegree === "full" && styles.chipTextSelected]}>
                        Fully automated
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.chip, automationDegree === "reviewed" && styles.chipSelected]}
                      onPress={() => setAutomationDegree("reviewed")}
                    >
                      <Text style={[styles.chipText, automationDegree === "reviewed" && styles.chipTextSelected]}>
                        Human reviews first
                      </Text>
                    </TouchableOpacity>
                  </View>
                </>
              )}

              <Text style={styles.fieldLabel}>GitHub repo (optional)</Text>
              <TextInput
                style={styles.input}
                value={githubUrl}
                onChangeText={setGithubUrl}
                placeholder="https://github.com/owner/repo"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
              />

              <TouchableOpacity style={styles.submitButton} onPress={handleSubmit} disabled={busy}>
                <Text style={styles.submitButtonText}>{busy ? "Checking compliance…" : "Add & Check Compliance"}</Text>
              </TouchableOpacity>
            </ScrollView>
          ) : (
            <ScrollView>
              <Text style={styles.resultsIntro}>
                Added to the knowledge base. Here's what LegalGuard's keyword matcher found -- confirm these on the
                Impact Diff tab before initializing a guardrail repo:
              </Text>
              {matches.length === 0 && (
                <Text style={styles.emptyText}>No candidate regulations matched yet. Check back after the next ingestion run, or browse Impact Diff manually.</Text>
              )}
              {matches.map((m) => (
                <View key={m.reg_id} style={styles.matchCard}>
                  <Text style={styles.matchTitle}>{m.official_title}</Text>
                  <Text style={styles.matchMeta}>
                    {m.jurisdiction} · {m.issuing_body} · match score {m.score}
                  </Text>
                </View>
              ))}
              <TouchableOpacity style={styles.submitButton} onPress={handleClose}>
                <Text style={styles.submitButtonText}>Done</Text>
              </TouchableOpacity>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
}

function UseCaseCard({ useCase }) {
  const Icon = MODALITY_ICON[useCase.modality] || Database;
  const riskTier = useCase.risk_tier || "unclassified";
  const riskStyle = RISK_TIER_STYLE[riskTier] || RISK_TIER_STYLE.unclassified;
  return (
    <View style={styles.card}>
      <View style={styles.cardTopRow}>
        <View style={styles.iconBadge}>
          <Icon size={14} color={colors.primary} />
        </View>
        <View style={{ flexDirection: "row", gap: 6 }}>
          {useCase.source === "user_submitted" && <MetadataPill label="YOURS" variant="warning" />}
          <MetadataPill label={useCase.parent_sector} variant="info" />
        </View>
      </View>
      <Text style={styles.cardTitle}>{useCase.name}</Text>
      {!!useCase.description && <Text style={styles.cardDescription}>{useCase.description}</Text>}
      <View style={styles.cardFooterRow}>
        <MetadataPill
          label={riskTier.replace("_", " ").toUpperCase()}
          backgroundColor={riskStyle.background}
          textColor={riskStyle.color}
        />
        <MetadataPill label={(useCase.modality || "").replace("_", " ").toUpperCase()} variant="info" />
        {/* Real signal read from this use case's own GitHub repo (a detected
            agent framework, or its primary language) -- see
            ingestion/enrich_architecture.py. Omitted, not guessed, when
            there's no linked repo or nothing usable was found there. */}
        {!!useCase.architecture_signal && (
          <MetadataPill label={useCase.architecture_signal.toUpperCase()} variant="primary" icon={Cpu} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: 20,
    marginTop: 16,
    backgroundColor: colors.surface,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  searchInput: { flex: 1, fontFamily: type.fontFamily, fontSize: 13, color: colors.textMain },
  addButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.button,
    padding: 6,
  },
  emptyText: { fontFamily: type.fontFamily, color: colors.textMuted, textAlign: "center", marginTop: 40 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 12,
  },
  cardTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  iconBadge: {
    backgroundColor: "#F1F5F9",
    padding: 6,
    borderRadius: 6,
  },
  cardTitle: { fontFamily: type.fontFamilyBold, fontSize: 14, color: colors.textMain, marginBottom: 4 },
  cardDescription: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, marginBottom: 10 },
  cardFooterRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  modalBackdrop: { flex: 1, backgroundColor: "#0B254599", justifyContent: "flex-end" },
  modalSheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: "85%",
  },
  modalHeaderRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  modalTitle: { fontFamily: type.fontFamilyBold, fontSize: 16, color: colors.textMain },
  fieldLabel: {
    fontFamily: type.fontFamilyMedium,
    fontSize: 11,
    color: colors.secondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.button,
    padding: 10,
    fontFamily: type.fontFamily,
    fontSize: 13,
    color: colors.textMain,
  },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.chip,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: colors.surface,
  },
  chipSelected: { borderColor: colors.accent, backgroundColor: "#FFD16615" },
  chipText: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted, textTransform: "capitalize" },
  chipTextSelected: { color: colors.primary, fontFamily: type.fontFamilyMedium },
  submitButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.button,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 20,
    marginBottom: 8,
  },
  submitButtonText: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.primary },
  resultsIntro: { fontFamily: type.fontFamily, fontSize: 12, color: colors.textMuted, lineHeight: 17, marginBottom: 12 },
  matchCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: 12,
    marginBottom: 8,
  },
  matchTitle: { fontFamily: type.fontFamilyMedium, fontSize: 13, color: colors.textMain, marginBottom: 2 },
  matchMeta: { fontFamily: type.fontFamily, fontSize: 11, color: colors.textMuted },
});
