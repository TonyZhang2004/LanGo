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

    def test_theme_uses_brown_selected_states(self):
        self.assertEqual(pi_screen.THEME["paper"], "#f7f3eb")
        self.assertEqual(pi_screen.THEME["ink"], "#151719")
        self.assertEqual(pi_screen.THEME["accent"], "#6a4128")
        self.assertEqual(pi_screen.THEME["accent_strong"], "#4d2c18")
        self.assertEqual(pi_screen.THEME["accent_soft"], "#e8d5c2")
        self.assertNotIn("accent_blue", pi_screen.THEME)

    def test_navigation_icon_switches_between_gear_and_home(self):
        self.assertEqual(pi_screen.navigation_icon(False), pi_screen.GEAR_ICON)
        self.assertEqual(pi_screen.navigation_icon(True), pi_screen.HOME_ICON)

    def test_settings_switcher_is_sized_as_primary_control(self):
        self.assertEqual(pi_screen.SWITCHER_BAR_RELWIDTH, 0.76)
        self.assertEqual(pi_screen.SWITCHER_BAR_HEIGHT, 104)
        self.assertEqual(pi_screen.SWITCHER_BUTTON_WIDTH, 170)
        self.assertEqual(pi_screen.SWITCHER_BUTTON_HEIGHT, 80)

    def test_fallback_language_source_matches_backend_supported_languages(self):
        languages = pi_screen.language_options()
        language_keys = {language["key"] for language in languages}

        self.assertEqual(
            language_keys,
            {"arabic", "chinese", "french", "japanese", "russian", "spanish"},
        )

    def test_main_message_uses_pending_translation_when_selected(self):
        message = pi_screen.format_main_message(
            "learn",
            {"english": "hi", "translated": "hola"},
            None,
        )

        self.assertEqual(message, "hi → hola")

    def test_main_message_defaults_to_start_prompt(self):
        message = pi_screen.format_main_message("learn", None, None)

        self.assertEqual(message, "point to start translating")

    def test_main_message_uses_game_placeholder_for_game_mode(self):
        message = pi_screen.format_main_message("game", None, None)

        self.assertEqual(message, "game mode coming soon")

    def test_touch_fonts_are_sized_for_small_screen_finger_targets(self):
        self.assertGreaterEqual(pi_screen.TOUCH_FONT[1], 24)
        self.assertGreaterEqual(pi_screen.TOUCH_FONT_SMALL[1], 22)
        self.assertEqual(pi_screen.MODE_TILE_SIZE, 180)


if __name__ == "__main__":
    unittest.main()
