export type User = {
  id: string;
  name: string;
  email: string;
  created_at?: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type Product = {
  id: string;
  user_id: string;
  name: string;
  description: string;
  image_url: string | null;
  created_at?: string;
};

export type AnalysisStatus =
  | "pending"
  | "feature_extraction"
  | "patent_search"
  | "analysis"
  | "design_generation"
  | "completed"
  | "failed";

export type PatentHit = {
  patent_number: string;
  title: string;
  abstract: string;
  filing_date?: string | null;
  publication_date?: string | null;
  inventors: string[];
  assignee?: string | null;
  claims: string;
  source: string;
  source_url: string;
  relevance_score: number;
  matching_features: string[];
};

export type ClaimMapping = {
  patent_id: string;
  claim_id: string;
  claim_element: string;
  product_feature: string;
  strength: string;
  explanation: string;
};

export type ProsecutorOutput = {
  risk_claims: { patent_id: string; claim_id: string; risk_level: string; reason: string }[];
  claim_element_mappings: ClaimMapping[];
  confidence_per_patent: { patent_id: string; confidence: number; explanation: string }[];
};

export type DefenderOutput = {
  distinctions: { claim_element: string; distinction: string; reasoning: string }[];
  prior_art_gaps: { claim_element: string; gap: string; reasoning: string }[];
  weak_claim_elements: { claim_element: string; reasoning: string; risk: string }[];
  overall_assessment: string;
  confidence: number;
  disclaimer: string;
};

export type DesignAlternative = {
  id: number;
  description: string;
  avoids_claim_element: string;
  changes_from_original: string[];
  tradeoff: string;
  why_it_differs: string;
  risk_reduction_rationale: string;
  design_generation_prompt: string;
};

export type RiskItem = {
  claim_element: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  score: number;
  reason: string;
  supporting_patents: string[];
  prior_art_overlap?: string | null;
  distinction?: string | null;
  recommended_action?: string | null;
};

export type RiskMatrix = {
  status: string;
  overall_score: number | null;
  overall_risk: "LOW" | "MEDIUM" | "HIGH" | null;
  risks: RiskItem[];
};

export type RedesignImage = {
  option_id: number;
  image_url: string | null;
  status: string;
  error?: string | null;
  prompt_used?: string;
};

export type FinalReport = {
  executive_summary: string;
  key_risks: string[];
  important_uncertainties: string[];
  recommended_next_steps: string[];
  attorney_questions: string[];
  product_summary: string;
  extracted_features: any[];
  top_patents: PatentHit[];
  prosecutor_findings: ProsecutorOutput;
  defender_findings: DefenderOutput;
  claim_mappings: ClaimMapping[];
  risk_matrix: RiskMatrix;
  design_alternatives: DesignAlternative[];
  redesign_concepts: RedesignImage[];
  legal_disclaimer: string;
};

export type AnalysisDetail = {
  id: string;
  product_id: string;
  status: AnalysisStatus;
  created_at?: string;
  completed_at?: string | null;
  feature_extraction: any | null;
  patent_search: any | null;
  patents: PatentHit[];
  prosecutor: ProsecutorOutput | null;
  defender: DefenderOutput | null;
  design: { alternatives: DesignAlternative[]; legal_disclaimer?: string } | null;
  risk_matrix: RiskMatrix | null;
  report: FinalReport | null;
  images: RedesignImage[];
  errors: { stage?: string; message?: string }[];
};

export type PipelineEvent = {
  type: string;
  stage?: string | null;
  data?: any;
  message?: string | null;
  seq: number;
  ts: string;
};
