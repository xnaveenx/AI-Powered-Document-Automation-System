import re
import redis
import json
from typing import Dict, List
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database.models import SessionLocal, ClassificationRule
from backend.common.config import Settings

# Redis client for caching rules
r = redis.Redis(host=Settings.REDIS_HOST, port=Settings.REDIS_PORT, decode_responses=True)

class RuleBasedClassifier:
    def __init__(self):
        # Default fallback rules
        self.default_rules = {
            "invoice": "Finance",
            "bill": "Finance",
            "resume": "Resume",
            "cv": "Resume",
            "agreement": "Legal",
            "contract": "Legal",
            "prescription": "Medical",
            "report": "Technical",
        }

    def _load_rules_from_db(self) -> Dict[str, str]:
        """
        Load all rules from DB or Redis cache.
        Returns: {keyword: category}
        """
        cache_key = "classification_rules"
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)

        db: Session = SessionLocal()
        try:
            rules = db.query(ClassificationRule).all()
            rules_dict = {r.keyword.lower(): r.category for r in rules}
            # Merge default rules
            rules_dict = {**self.default_rules, **rules_dict}
            # Cache in Redis for 1 hour
            r.setex(cache_key, 3600, json.dumps(rules_dict))
            return rules_dict
        finally:
            db.close()

    def get_applicable_rules(self, text: str) -> Dict:
        """
        Scan text for rule matches.
        Returns a dict with forced_category if any keyword is found.
        """
        rules = self._load_rules_from_db()
        text_lower = text.lower()

        for keyword, category in rules.items():
            if re.search(rf"\b{keyword}\b", text_lower):
                return {"forced_category": category, "matched_keyword": keyword}

        return {}

    def suggest_categories(self, text: str) -> List[str]:
        """
        Suggest possible categories by scanning all matches.
        """
        rules = self._load_rules_from_db()
        text_lower = text.lower()
        matches = [category for k, category in rules.items() if k in text_lower]
        return list(set(matches))  # unique categories

    # -------- Methods to manage rules --------
    def add_rule(self, keyword: str, category: str, created_by: str = None):
        db: Session = SessionLocal()
        try:
            # Add or update rule
            existing = db.query(ClassificationRule).filter_by(keyword=keyword.lower()).first()
            if existing:
                existing.category = category
            else:
                new_rule = ClassificationRule(keyword=keyword.lower(), category=category, created_by=created_by)
                db.add(new_rule)
            db.commit()
            # Invalidate Redis cache
            r.delete("classification_rules")
        finally:
            db.close()

    def remove_rule(self, keyword: str):
        db: Session = SessionLocal()
        try:
            rule = db.query(ClassificationRule).filter_by(keyword=keyword.lower()).first()
            if rule:
                db.delete(rule)
                db.commit()
                r.delete("classification_rules")  # Invalidate cache
        finally:
            db.close()
