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

    def test_visible_pending_items_limits_homepage_to_single_item(self):
        items = [{"pendingId": str(index)} for index in range(7)]

        visible = pi_screen.visible_pending_items(items)

        self.assertEqual([item["pendingId"] for item in visible], ["0"])

    def test_format_pending_label_combines_english_and_translation(self):
        label = pi_screen.format_pending_label({"english": "word", "translated": "trans"})

        self.assertEqual(label, "word → trans")

    def test_truncate_copy_adds_ellipsis_for_long_text(self):
        shortened = pi_screen.truncate_copy("Mandarin Chinese translation", 16)

        self.assertEqual(shortened, "Mandarin Chines…")

    def test_compact_language_label_shortens_mandarin_chinese(self):
        self.assertEqual(pi_screen.compact_language_label("Mandarin Chinese"), "Mandarin")
        self.assertEqual(pi_screen.compact_language_label("Spanish"), "Spanish")

    def test_queue_position_label_uses_compact_fraction_format(self):
        pending = [
            {"pendingId": "one"},
            {"pendingId": "two"},
            {"pendingId": "three"},
        ]

        label = pi_screen.queue_position_label(pending, "two")

        self.assertEqual(label, "2/3")

    def test_queue_navigation_only_shows_for_multiple_pending_items(self):
        self.assertFalse(pi_screen.should_show_queue_navigation([{"pendingId": "one"}]))
        self.assertTrue(
            pi_screen.should_show_queue_navigation(
                [{"pendingId": "one"}, {"pendingId": "two"}]
            )
        )

    def test_resolve_window_mode_accepts_windowed(self):
        self.assertEqual(pi_screen.resolve_window_mode("windowed"), "windowed")
        self.assertEqual(pi_screen.resolve_window_mode("fullscreen"), "fullscreen")

    def test_resolve_window_mode_falls_back_to_fullscreen_for_invalid_values(self):
        self.assertEqual(pi_screen.resolve_window_mode("tiny"), "fullscreen")

    def test_selected_pending_item_returns_selected_queue_item(self):
        pending = [
            {"pendingId": "one", "english": "apple"},
            {"pendingId": "two", "english": "pear"},
        ]

        selected = pi_screen.selected_pending_item(pending, "two")

        self.assertEqual(selected["english"], "pear")

    def test_settings_switcher_is_compact_for_small_screen(self):
        self.assertEqual(pi_screen.SWITCHER_BAR_RELWIDTH, 0.84)
        self.assertEqual(pi_screen.SWITCHER_BAR_HEIGHT, 68)
        self.assertEqual(pi_screen.SWITCHER_BUTTON_WIDTH, 124)
        self.assertEqual(pi_screen.SWITCHER_BUTTON_HEIGHT, 52)

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

    def test_touch_controls_fit_small_screen_targets(self):
        self.assertGreaterEqual(pi_screen.TOUCH_FONT[1], 20)
        self.assertGreaterEqual(pi_screen.TOUCH_FONT_SMALL[1], 18)
        self.assertEqual(pi_screen.MODE_TILE_SIZE, 124)
        self.assertEqual(pi_screen.MAX_HOME_PENDING, 1)
        self.assertEqual(pi_screen.QUEUE_GRID_COLUMNS, 1)
        self.assertGreaterEqual(pi_screen.QUEUE_ACTION_HEIGHT, 60)
        self.assertGreaterEqual(pi_screen.QUEUE_NAV_BUTTON_HEIGHT, 36)
        self.assertEqual(pi_screen.NAV_BUTTON_SIZE, 42)


if __name__ == "__main__":
    unittest.main()
