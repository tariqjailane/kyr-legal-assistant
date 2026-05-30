import os
import unittest
from nlp_engine import nlp_engine
from legal_db import init_db, get_answer_by_intent

class TestKYRSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Initializing DB...")
        init_db()
        print("Loading NLP models...")
        nlp_engine.load_models()

    def test_intent_recognition_english(self):
        query = "Landlord didn't give back deposit"
        intent, conf, debug_info = nlp_engine.predict_intent(query)
        print(f"Query: '{query}' -> Intent: {intent} (Conf: {conf})")
        self.assertEqual(intent, "tenant_rights")

    def test_intent_recognition_hindi(self):
        query = "मकान मालिक पैसे वापस नहीं कर रहा" # Slightly different from training data
        intent, conf, debug_info = nlp_engine.predict_intent(query)
        print(f"Query: '{query}' -> Intent: {intent} (Conf: {conf})")
        
        # If model is loaded, we expect semantic match. If fallback, it might fail if keywords don't match exactly.
        # But 'मकान मालिक' matches.
        self.assertIsNotNone(intent)
        if intent:
            self.assertEqual(intent, "tenant_rights")

    def test_db_retrieval(self):
        ans, cit, cs = get_answer_by_intent("domestic_violence", "ta")
        self.assertTrue("வன்முறை" in ans or "பாதுகாப்பு" in ans)
        print(f"Tamil Answer: {ans}")

if __name__ == '__main__':
    unittest.main()
