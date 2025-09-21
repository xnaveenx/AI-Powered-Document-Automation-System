import logging
import requests
from typing import Dict
from backend.common.config import Settings

logger = logging.getLogger(__name__)

# Load Gemini API key from Settings
GEMINI_API_KEY = Settings.GEMINI_API_KEY
GEMINI_API_URL = "https://api.gemini.ai/v1/classify"  # replace with actual endpoint

def classify_with_api(text: str) -> Dict:
    """
    Fallback document classification using Gemini API.
    Returns a dictionary: {category, confidence, details}
    """
    if not GEMINI_API_KEY:
        logger.error("Gemini API key not set in environment variables.")
        return {
            "category": "Unknown",
            "confidence": 0,
            "details": "No API key available for Gemini API"
        }

    try:
        headers = {
            "Authorization": f"Bearer {GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Adjust the keys according to the Gemini API response
        return {
            "category": data.get("category", "Unknown"),
            "confidence": data.get("confidence", 0),
            "details": "Classified using Gemini API"
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        return {
            "category": "Unknown",
            "confidence": 0,
            "details": f"API request error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in Gemini API classification: {e}")
        return {
            "category": "Unknown",
            "confidence": 0,
            "details": f"Unexpected API error: {str(e)}"
        }
