"""ClaimBreaker Agent 1 public interface."""
from .feature_extractor import extract_features, extract_features_from_image_bytes
from .models import EvidenceType, FeatureExtractionResult, PatentResult, PatentSearchResult, TechnicalFeature
from .patent_search import GooglePatentsSearch
__all__ = ["EvidenceType", "FeatureExtractionResult", "GooglePatentsSearch", "PatentResult", "PatentSearchResult", "TechnicalFeature", "extract_features", "extract_features_from_image_bytes"]
