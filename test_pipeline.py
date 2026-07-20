import unittest
import os
import json
import sqlite3
from unittest.mock import patch, MagicMock

# Import pipeline components
import db
import extractor
import personalizer
import dispatcher

class TestZeroCostRevenueEngine(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Override DB path for tests to a test database
        db.DB_PATH = "test_leads.db"
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        # Remove test database after tests
        if os.path.exists("test_leads.db"):
            os.remove("test_leads.db")

    def setUp(self):
        # Clean tables before each test
        conn = db.get_db_connection()
        conn.execute("DELETE FROM leads")
        conn.execute("DELETE FROM settings")
        conn.commit()
        conn.close()

    def test_database_lifecycle_and_deduplication(self):
        """Test database initialization, inserts, and duplicate prevention."""
        # Insert unique lead
        success = db.add_lead("Stripe", "stripe.com")
        self.assertTrue(success)
        
        # Ingesting same domain must fail (uniqueness check)
        success_dup = db.add_lead("Stripe Inc", "stripe.com")
        self.assertFalse(success_dup)

        # Get lead status
        leads = db.get_all_leads()
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "Discovered")
        self.assertEqual(leads[0]["company_name"], "Stripe")

    def test_database_status_updates(self):
        """Test transitioning lead status through state progression."""
        db.add_lead("Google", "google.com")
        leads = db.get_all_leads()
        lead_id = leads[0]["id"]
        
        # Transition 1: Enriched
        mock_meta = {"title": "Google", "description": "Search"}
        db.update_lead_enrichment(lead_id, mock_meta, "contact@google.com", "Tech", "Enriched")
        
        lead = db.get_lead(lead_id)
        self.assertEqual(lead["status"], "Enriched")
        self.assertEqual(lead["recipient_email"], "contact@google.com")
        self.assertEqual(json.loads(lead["extracted_metadata"])["title"], "Google")

        # Transition 2: AI output / Pending Review
        db.update_lead_ai_output(lead_id, ["Pain A", "Pain B"], "Hey Google", "Body copy", "Pending_Review")
        lead = db.get_lead(lead_id)
        self.assertEqual(lead["status"], "Pending_Review")
        self.assertEqual(lead["personalized_subject"], "Hey Google")
        self.assertIn("Pain A", json.loads(lead["pain_points"]))

        # Transition 3: Completed
        db.update_lead_status(lead_id, "Completed")
        lead = db.get_lead(lead_id)
        self.assertEqual(lead["status"], "Completed")

    def test_settings_storage(self):
        """Test saving and retrieving configuration keys."""
        # Environment fallback
        os.environ["TEST_ENV_KEY"] = "EnvVal"
        val = db.get_setting("TEST_ENV_KEY")
        self.assertEqual(val, "EnvVal")
        
        # DB storage
        db.save_setting("GEMINI_API_KEY", "AIzaTestKey")
        val_db = db.get_setting("GEMINI_API_KEY")
        self.assertEqual(val_db, "AIzaTestKey")

    def test_extractor_parser(self):
        """Test HTML parser with mock HTML content."""
        html_content = """
        <html>
            <head>
                <title>Test Title</title>
                <meta name="description" content="This is a test website description.">
            </head>
            <body>
                <h1>Welcome to test site</h1>
                <h2>Our services</h2>
                <p>Contact us at info@mytestdomain.com or sales@mytestdomain.com</p>
            </body>
        </html>
        """
        parser = extractor.MetadataParser()
        parser.feed(html_content)
        
        self.assertEqual(parser.title, "Test Title")
        self.assertEqual(parser.meta_description, "This is a test website description.")
        self.assertIn("H1: Welcome to test site", parser.headings)
        
        # Test full regex emails check on parser output text
        full_text = " ".join(parser.text_content)
        import re
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
        self.assertIn("info@mytestdomain.com", emails)
        self.assertIn("sales@mytestdomain.com", emails)

    @patch('smtplib.SMTP')
    def test_dispatcher_success(self, mock_smtp):
        """Test SMTP email sender executes connections and commands properly."""
        db.save_setting("SMTP_HOST", "smtp.test.com")
        db.save_setting("SMTP_PORT", "587")
        db.save_setting("SMTP_USER", "test@test.com")
        db.save_setting("SMTP_PASSWORD", "secret")
        db.save_setting("SMTP_FROM_EMAIL", "test@test.com")
        
        # Mock connection sequence
        instance = mock_smtp.return_value
        instance.has_extn.return_value = True
        
        success = dispatcher.send_email("recipient@domain.com", "Subject", "Body")
        self.assertTrue(success)
        
        # Verify connection was established and closed
        instance.login.assert_called_with("test@test.com", "secret")
        instance.sendmail.assert_called_once()
        instance.quit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
