import unittest

import pi_screen


class PiScreenHelperTests(unittest.TestCase):
    def test_choose_selected_pending_id_keeps_existing_selection(self):
        pending = [
            {"pendingId": "one"},
            {"pendingId": "two"},
        ]

        selected = pi_screen.choose_selected_pending_id(pending, "two")

        self.assertEqual(selected, "two")

    def test_choose_selected_pending_id_falls_back_to_first_pending(self):
        pending = [
            {"pendingId": "one"},
            {"pendingId": "two"},
        ]

        selected = pi_screen.choose_selected_pending_id(pending, "missing")

        self.assertEqual(selected, "one")

    def test_choose_selected_pending_id_returns_none_for_empty_queue(self):
        self.assertIsNone(pi_screen.choose_selected_pending_id([], "anything"))

    def test_theme_uses_webapp_aligned_tokens(self):
        self.assertEqual(pi_screen.THEME["paper"], "#f7f3eb")
        self.assertEqual(pi_screen.THEME["ink"], "#151719")
        self.assertEqual(pi_screen.THEME["accent"], "#d7ff5c")


if __name__ == "__main__":
    unittest.main()
