"""VeriFact — open-source credibility engine for news, web content & social media."""

from .models import CredibilityReport, Verdict
from .pipeline import analyze_image, analyze_text, analyze_url

__version__ = "0.1.0"
__all__ = ["CredibilityReport", "Verdict", "analyze_image", "analyze_text", "analyze_url", "__version__"]
