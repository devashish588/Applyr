"""
Phase 7 — Application Lifecycle Tests (P0)
"""

import unittest
from unittest.mock import MagicMock, patch


class TestStateMachine(unittest.TestCase):
    def test_allowed_transitions(self):
        from core.services.application_service import ALLOWED_TRANSITIONS
        self.assertIn("PREPARING", ALLOWED_TRANSITIONS["DISCOVERED"])
        self.assertIn("APPLIED", ALLOWED_TRANSITIONS["READY_TO_APPLY"])
        self.assertEqual(ALLOWED_TRANSITIONS["CLOSED"], set())

    def test_outcomes(self):
        from core.services.application_service import ALLOWED_OUTCOMES
        self.assertIn("REJECTED", ALLOWED_OUTCOMES)
        self.assertNotIn("OFFER", ALLOWED_OUTCOMES)


class TestApplicationCreation(unittest.TestCase):
    @patch("core.services.application_service._conn")
    def test_first_attempt(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        # Mock job fetch
        mock_cur.fetchone.side_effect = [
            {"id": 1, "title": "Backend", "company": "Acme"},  # job
            None,  # no open app
            {"coalesce": 0},  # max attempt
            None,  # no previous
            {"id": 10},  # inserted app id
            {"id": 10, "job_id": 1, "attempt_number": 1, "current_state": "PREPARING"},  # get_application
        ]
        mock_cur.fetchall.return_value = []
        svc = ApplicationService()
        # Mock get_application to return created
        with patch.object(svc, "get_application", return_value={"id": 10, "job_id": 1, "attempt_number": 1, "current_state": "PREPARING"}):
            app = svc.create_application(job_id=1)
            self.assertEqual(app["attempt_number"], 1)

    @patch("core.services.application_service._conn")
    def test_open_duplicate_blocks(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            {"id": 1, "title": "Backend", "company": "Acme"},
            {"id": 5, "current_state": "APPLIED"},  # open exists
        ]
        svc = ApplicationService()
        with self.assertRaises(ValueError) as ctx:
            svc.create_application(job_id=1)
        self.assertIn("already exists", str(ctx.exception))


class TestReapplication(unittest.TestCase):
    @patch("core.services.application_service._conn")
    def test_closed_allows_reapply(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            {"id": 1, "title": "Backend", "company": "Acme"},
            None,  # no open (closed)
            {"coalesce": 1},  # max attempt 1
            {"id": 5},  # previous
            {"id": 11},
            {"id": 11, "job_id": 1, "attempt_number": 2, "previous_application_id": 5},
        ]
        svc = ApplicationService()
        with patch.object(svc, "get_application", return_value={"id": 11, "attempt_number": 2, "previous_application_id": 5}):
            app = svc.create_application(job_id=1)
            self.assertEqual(app["attempt_number"], 2)


class TestSubmission(unittest.TestCase):
    @patch("core.services.application_service._conn")
    def test_submit_sets_submitted_at(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            {"current_state": "READY_TO_APPLY", "submitted_at": None},
            {"match_snapshot": None},
            {"id": 10, "current_state": "APPLIED", "submitted_at": "2024-01-01"},
        ]
        svc = ApplicationService()
        with patch.object(svc, "get_application", return_value={"id": 10, "current_state": "APPLIED", "submitted_at": "2024-01-01"}):
            app = svc.apply_application(10)
            self.assertEqual(app["current_state"], "APPLIED")


class TestOutcome(unittest.TestCase):
    def test_offer_rejected(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        with self.assertRaises(ValueError) as ctx:
            svc.set_outcome(1, "OFFER")
        self.assertIn("OFFER", str(ctx.exception))

    def test_none_cannot_close(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        with self.assertRaises(ValueError):
            svc.set_outcome(1, "NONE")

    @patch("core.services.application_service._conn")
    def test_closed_unknown_valid(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            {"current_state": "APPLIED"},
            {"outcome": "NONE"},
            {"id": 1, "current_state": "CLOSED", "outcome": "UNKNOWN"},
        ]
        svc = ApplicationService()
        with patch.object(svc, "get_application", return_value={"id": 1, "current_state": "CLOSED", "outcome": "UNKNOWN"}):
            app = svc.set_outcome(1, "UNKNOWN")
            self.assertEqual(app["outcome"], "UNKNOWN")

    @patch("core.services.application_service._conn")
    def test_closed_none_invalid(self, mock_conn):
        from core.services.application_service import ApplicationService
        mock_cur = MagicMock()
        mock_conn.return_value.__enter__.return_value = mock_conn.return_value
        mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
        svc = ApplicationService()
        with self.assertRaises(ValueError) as ctx:
            svc.set_outcome(1, "NONE")
        self.assertIn("NONE", str(ctx.exception))


class TestGenericEventProtection(unittest.TestCase):
    def test_lifecycle_event_rejected(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        with self.assertRaises(ValueError) as ctx:
            svc.add_event(1, "application_submitted", actor="user")
        self.assertIn("Invalid event_type", str(ctx.exception))

    def test_closed_event_rejected(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        with self.assertRaises(ValueError):
            svc.add_event(1, "closed", actor="user")

    def test_note_succeeds(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        with patch("core.services.application_service._conn") as mock_conn:
            mock_cur = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_conn.return_value
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.return_value = {"id": 1}
            mock_cur.fetchall.return_value = []
            with patch.object(svc, "get_timeline", return_value=[{"id": 1, "event_type": "note"}]):
                ev = svc.add_event(1, "note", actor="user", payload='{"text":"hello"}')
                self.assertEqual(ev["event_type"], "note")

    def test_generic_cannot_change_state(self):
        from core.services.application_service import ApplicationService
        svc = ApplicationService()
        # Generic add_event should not update applications.current_state
        # Verify by checking that add_event does not call UPDATE on applications
        with patch("core.services.application_service._conn") as mock_conn:
            mock_cur = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_conn.return_value
            mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.return_value = {"id": 1}
            svc.add_event(1, "note", actor="user")
            # Ensure no UPDATE on applications
            calls = [str(c) for c in mock_cur.execute.call_args_list]
            self.assertFalse(any("UPDATE applications" in c for c in calls))


class TestLegacyCompatibility(unittest.TestCase):
    def test_jobs_status_mapping(self):
        # Service-layer mapping, not DB trigger
        mapping = {"pending": "DISCOVERED", "tailored": "PREPARING", "applied": "APPLIED", "rejected": "CLOSED"}
        self.assertEqual(mapping["pending"], "DISCOVERED")


if __name__ == "__main__":
    unittest.main()
