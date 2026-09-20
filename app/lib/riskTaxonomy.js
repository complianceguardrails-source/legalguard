// Generated from ingestion/risk_taxonomy.py -- do not edit by hand; regenerate
// with the snippet in that file's docstring so labels and descriptions stay
// identical to what the ingestion stores. Slugs are the stored values.

export const RISK_FAMILIES = [
  {
    "key": "systemic",
    "label": "Macroprudential & systemic market"
  },
  {
    "key": "model",
    "label": "Operational, quantitative & model"
  },
  {
    "key": "cyber",
    "label": "Cybersecurity, data security & fraud"
  },
  {
    "key": "legal",
    "label": "Legal, regulatory & compliance"
  },
  {
    "key": "vendor",
    "label": "Vendor & third-party reliance"
  },
  {
    "key": "ethical",
    "label": "Ethical, social & reputational"
  },
  {
    "key": "environmental",
    "label": "Environmental & climate sustainability"
  }
];

export const RISKS = [
  {
    "slug": "herding_behavior",
    "family": "systemic",
    "label": "Herding behavior",
    "description": "Multiple financial institutions deploy identical off-the-shelf base models, leading to synchronized market movements."
  },
  {
    "slug": "model_convergence",
    "family": "systemic",
    "label": "Model convergence",
    "description": "Algorithms train on the same public data pools, causing identical automated reactions during market stress."
  },
  {
    "slug": "liquidity_dry_ups",
    "family": "systemic",
    "label": "Sudden liquidity dry-ups",
    "description": "Synchronized algorithmic selling completely exhausts market buyers in seconds."
  },
  {
    "slug": "flash_crashes",
    "family": "systemic",
    "label": "Automated flash crashes",
    "description": "High-speed, identical model responses trigger rapid, cascading asset price collapses."
  },
  {
    "slug": "procyclicality",
    "family": "systemic",
    "label": "Procyclicality",
    "description": "AI systems optimized on real-time variables accidentally amplify current market trends."
  },
  {
    "slug": "market_spirals",
    "family": "systemic",
    "label": "Algorithmic acceleration of market spirals",
    "description": "Trading models accelerate a downward market trajectory during panic selling."
  },
  {
    "slug": "asset_bubbles",
    "family": "systemic",
    "label": "Artificial asset bubble generation",
    "description": "Momentum-driven analytics tools overheat specific asset classes during market booms."
  },
  {
    "slug": "hidden_interconnectedness",
    "family": "systemic",
    "label": "Invisible data-driven interconnectedness",
    "description": "The widespread use of alternative data creates hidden correlations between unrelated asset classes."
  },
  {
    "slug": "synthetic_correlation",
    "family": "systemic",
    "label": "Synthetic portfolio correlation",
    "description": "Analytics engines incorrectly treat diverse portfolios as diversified when they actually share underlying data dependencies."
  },
  {
    "slug": "geopolitical_brittleness",
    "family": "systemic",
    "label": "Geopolitical model brittleness",
    "description": "AI systems fail because they lack a conceptual understanding of black swan world events."
  },
  {
    "slug": "regime_shift_failure",
    "family": "systemic",
    "label": "Macroeconomic regime shift failures",
    "description": "Models degrade unexpectedly when historical training patterns are broken by structural shifts like sudden inflation."
  },
  {
    "slug": "black_box",
    "family": "model",
    "label": "The black box problem",
    "description": "Complex deep learning architectures prevent humans from tracing the exact path to a decision."
  },
  {
    "slug": "lack_of_explainability",
    "family": "model",
    "label": "Lack of explainability",
    "description": "Risk managers cannot isolate the precise cause-and-effect rationale behind a model's output."
  },
  {
    "slug": "auditing_barriers",
    "family": "model",
    "label": "Auditing barriers",
    "description": "Internal compliance teams cannot validate opaque credit models for regulatory review."
  },
  {
    "slug": "hallucinations",
    "family": "model",
    "label": "Generative hallucinations",
    "description": "Large language models confidently manufacture false financial statistics."
  },
  {
    "slug": "confident_misinformation",
    "family": "model",
    "label": "Confident misinformation",
    "description": "AI assistants invent fictitious historical interest rates or corporate performance metrics."
  },
  {
    "slug": "data_drift",
    "family": "model",
    "label": "Data drift",
    "description": "A model's predictive accuracy degrades because real-world economic conditions diverge from its training baseline."
  },
  {
    "slug": "concept_drift",
    "family": "model",
    "label": "Concept drift",
    "description": "The underlying statistical properties of the target variable change over time, rendering static models obsolete."
  },
  {
    "slug": "feedback_loops",
    "family": "model",
    "label": "Self-fulfilling feedback loops",
    "description": "High-frequency trading bots alter the very market dynamics they observe, corrupting future training data."
  },
  {
    "slug": "artificial_environment",
    "family": "model",
    "label": "Artificial environment optimization",
    "description": "Algorithms optimize for a distorted market environment that they created themselves."
  },
  {
    "slug": "skills_atrophy",
    "family": "model",
    "label": "Human skills atrophy",
    "description": "Complete reliance on automated analytics degrades the fundamental qualitative judgment of human analyst teams."
  },
  {
    "slug": "operational_blind_spots",
    "family": "model",
    "label": "Operational blind spots",
    "description": "Institutions face catastrophic failure if automated software goes offline and staff lack the skills to take over manually."
  },
  {
    "slug": "biometric_spoofing",
    "family": "cyber",
    "label": "Biometric identity verification spoofing",
    "description": "Bad actors use high-fidelity AI video cloning to bypass visual KYC checks."
  },
  {
    "slug": "voice_clone_bypass",
    "family": "cyber",
    "label": "Voice clone authorization bypassing",
    "description": "Fraudsters use AI voice synthesis to defeat telephone banking security protocols."
  },
  {
    "slug": "synthetic_accounts",
    "family": "cyber",
    "label": "Synthetic bank account creation",
    "description": "Criminals combine deepfakes with stolen credentials to open un-trackable fraudulent accounts."
  },
  {
    "slug": "data_poisoning",
    "family": "cyber",
    "label": "Data poisoning",
    "description": "Malicious actors deliberately inject malformed data points into public feeds to corrupt financial models."
  },
  {
    "slug": "adversarial_manipulation",
    "family": "cyber",
    "label": "Adversarial manipulation",
    "description": "Attackers manipulate input data to trick underwriting bots into miscalculating risk."
  },
  {
    "slug": "proprietary_data_leakage",
    "family": "cyber",
    "label": "Proprietary data leakage",
    "description": "Employees feed corporate balance sheets into external generative tools, exposing trade secrets."
  },
  {
    "slug": "ip_exposure",
    "family": "cyber",
    "label": "Intellectual property exposure",
    "description": "Sensitive customer financial histories enter shared public model spaces through unencrypted prompts."
  },
  {
    "slug": "spear_phishing",
    "family": "cyber",
    "label": "Hyper-targeted spear-phishing",
    "description": "AI automates the creation of highly convincing, personalized emails that mimic executive leadership."
  },
  {
    "slug": "social_engineering",
    "family": "cyber",
    "label": "Automated corporate social engineering",
    "description": "AI bots systematically target vendor communication channels to trigger unauthorized wire transfers."
  },
  {
    "slug": "high_risk_designation",
    "family": "legal",
    "label": "High-risk designation liabilities",
    "description": "Credit-scoring systems trigger strict compliance burdens under global frameworks like the EU AI Act."
  },
  {
    "slug": "insurance_underwriting_penalties",
    "family": "legal",
    "label": "Insurance underwriting penalties",
    "description": "Automated insurance platforms face heavy fines if they fail to log conformity data."
  },
  {
    "slug": "human_oversight_audit_failure",
    "family": "legal",
    "label": "Human conformity audit failures",
    "description": "Firms penalised because they cannot prove active human oversight over autonomous pipelines."
  },
  {
    "slug": "professional_accountability",
    "family": "legal",
    "label": "Professional accountability gaps",
    "description": "Licensed professionals face personal legal liability when an AI assistant generates erroneous tax returns."
  },
  {
    "slug": "regulatory_reporting_errors",
    "family": "legal",
    "label": "Regulatory reporting errors",
    "description": "Automated compliance software submits incorrect financial data to oversight bodies, leading to censures."
  },
  {
    "slug": "copyright_infringement",
    "family": "legal",
    "label": "Copyright infringement",
    "description": "Finetuning localized models on paywalled market research documents triggers intellectual property lawsuits."
  },
  {
    "slug": "dataset_lawsuits",
    "family": "legal",
    "label": "Proprietary dataset lawsuits",
    "description": "Training models on scraping-restricted financial data pools results in breach-of-contract litigation."
  },
  {
    "slug": "provider_concentration",
    "family": "vendor",
    "label": "Service provider concentration",
    "description": "Financial institutions consolidate their heavy analytics workloads onto a tiny handful of cloud giants."
  },
  {
    "slug": "single_point_of_failure",
    "family": "vendor",
    "label": "Single-point-of-failure fragility",
    "description": "A single regional server outage at a dominant cloud provider disables critical live financial functions globally."
  },
  {
    "slug": "supply_chain_breach",
    "family": "vendor",
    "label": "Supply chain cyber breaches",
    "description": "Hackers exploit a vulnerability in a third-party AI vendor to gain lateral access to a bank's core infrastructure."
  },
  {
    "slug": "open_source_vulnerabilities",
    "family": "vendor",
    "label": "Hidden open-source vulnerabilities",
    "description": "Developers insert undocumented open-source AI libraries into workflows, introducing unmonitored backdoors."
  },
  {
    "slug": "lending_bias",
    "family": "ethical",
    "label": "Algorithmic lending bias",
    "description": "Financial AI models quietly reinforce historical, systemic discrimination against marginalized groups."
  },
  {
    "slug": "automated_redlining",
    "family": "ethical",
    "label": "Automated redlining",
    "description": "Credit scoring models reject loan applications from specific postcodes without an auditable reason."
  },
  {
    "slug": "predatory_targeting",
    "family": "ethical",
    "label": "Predatory micro-targeting",
    "description": "Behavioral analytics identify financially vulnerable consumers to pitch high-interest payday loans."
  },
  {
    "slug": "opportunistic_placement",
    "family": "ethical",
    "label": "Opportunistic product placement",
    "description": "Algorithms serve high-fee financial products to users at their moment of maximum economic distress."
  },
  {
    "slug": "consumer_alienation",
    "family": "ethical",
    "label": "Automated consumer alienation",
    "description": "Robotic financial advisors cause mass customer churn due to a lack of empathy or nuance."
  },
  {
    "slug": "credit_limit_cuts",
    "family": "ethical",
    "label": "Unjustified credit limit cuts",
    "description": "Abrupt, algorithmically driven reductions in credit lines trigger intense public and reputational backlash."
  },
  {
    "slug": "training_carbon",
    "family": "environmental",
    "label": "Carbon-intensive computational training",
    "description": "Training large language models requires millions of kilowatt-hours of fossil-fuel-powered electricity."
  },
  {
    "slug": "inference_energy",
    "family": "environmental",
    "label": "Continuous inference energy demands",
    "description": "Running 24/7 high-frequency trading simulations expands an institution's carbon footprint continuously."
  },
  {
    "slug": "scope2_inflation",
    "family": "environmental",
    "label": "Scope 2 emissions inflation",
    "description": "Massive data center power consumption directly prevents firms from meeting corporate Net-Zero targets."
  },
  {
    "slug": "greenwashing_allegations",
    "family": "environmental",
    "label": "Greenwashing allegations",
    "description": "High energy consumption patterns contradict public corporate sustainability marketing."
  },
  {
    "slug": "water_scarcity",
    "family": "environmental",
    "label": "Evaporative water scarcity",
    "description": "AI data centers consume millions of gallons of water daily for cooling, straining local reservoirs."
  },
  {
    "slug": "data_center_downtime",
    "family": "environmental",
    "label": "Data center operational downtime",
    "description": "Drought-prone regions enforce regulatory water restrictions, shutting down active financial pipelines."
  },
  {
    "slug": "e_waste",
    "family": "environmental",
    "label": "Accelerated e-waste cycles",
    "description": "Specialized AI graphics processing units become obsolete every 2 to 3 years, generating massive hazardous waste."
  },
  {
    "slug": "circular_economy_failures",
    "family": "environmental",
    "label": "Circular economy compliance failures",
    "description": "Rapid hardware replacement cycles undermine institutional waste management goals."
  },
  {
    "slug": "green_bleaching",
    "family": "environmental",
    "label": "AI-driven green-bleaching",
    "description": "Flawed ESG analytics tools misinterpret corporate disclosures and misclassify carbon-heavy assets as sustainable."
  },
  {
    "slug": "transition_portfolio_risk",
    "family": "environmental",
    "label": "Climate transition portfolio risk",
    "description": "Financial models exposed to severe losses when sudden carbon taxes hit misclassified \"green\" assets."
  },
  {
    "slug": "high_emission_optimization",
    "family": "environmental",
    "label": "High-emission algorithmic optimization",
    "description": "Asset allocation models route capital into fossil fuels because they optimize strictly for short-term yield."
  }
];

export const RISK_BY_SLUG = Object.fromEntries(RISKS.map((r) => [r.slug, r]));
