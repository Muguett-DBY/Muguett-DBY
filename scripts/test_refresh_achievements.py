"""Guard native-badge parsing against duplicates, unrelated images and failed fetches."""
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("refresh_achievements", Path(__file__).with_name("refresh-achievements.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", 64, 64)


def image(owner="Muguett-DBY", slug="pull-shark", source="https://github.githubassets.com/assets/pull-shark-bronze-example.png", name="Pull Shark"):
    return (
        f'<img data-hovercard-type="achievement" data-hovercard-url="/users/{owner}/achievements/{slug}/detail?hovercard=1" '
        f'src="{source}" alt="Achievement: {name}" />'
    )


class AchievementShowcaseTests(unittest.TestCase):
    def parse(self, markup):
        parser = module.AchievementParser("Muguett-DBY")
        parser.feed(markup)
        return parser.badges

    def test_native_sidebar_and_profile_duplicates_are_collapsed(self):
        badges = self.parse(image() * 3)
        self.assertEqual(list(badges), ["pull-shark"])
        self.assertEqual(badges["pull-shark"]["tier"], "bronze")

    def test_readme_badge_images_are_not_native_awards(self):
        self.assertEqual(self.parse('<img src="https://github.githubassets.com/assets/yolo-default-example.png" alt="Achievement: YOLO" />'), {})

    def test_other_accounts_are_not_credited(self):
        self.assertEqual(self.parse(image(owner="someone-else")), {})

    def test_external_image_hosts_are_rejected(self):
        for source in ("https://example.com/fake.png", "https://github.githubassets.com.example.com/fake.png", "javascript:alert(1)"):
            with self.subTest(source=source):
                self.assertEqual(self.parse(image(source=source)), {})

    def test_failed_or_empty_profile_does_not_erase_badges(self):
        for markup in ("", "<h1>Rate limit exceeded</h1>"):
            with self.subTest(markup=markup), self.assertRaises(ValueError):
                module.render_section("Muguett-DBY", self.parse(markup))

    def test_missing_markers_do_not_replace_unrelated_readme(self):
        with self.assertRaises(ValueError):
            module.replace_section("My profile", "replacement")

    def test_duplicate_markers_are_rejected(self):
        with self.assertRaises(ValueError):
            module.replace_section((module.START + module.END) * 2, "replacement")

    def test_only_the_showcase_block_is_replaced(self):
        original = "Before\n" + module.START + "old" + module.END + "\nAfter"
        section = module.render_section("Muguett-DBY", self.parse(image()))
        self.assertEqual(module.replace_section(original, section), "Before\n" + section + "\nAfter")
        self.assertIn("Pull Shark (Bronze)", section)
        self.assertIn("./assets/profile/achievements/pull-shark.svg", section)
        self.assertIn('alt="Pull Shark (Bronze), earned GitHub achievement"', section)
        self.assertNotIn("Starstruck", section)

    def test_showcase_cards_can_wrap_with_the_available_width(self):
        badges = self.parse("".join(image(slug=f"badge-{n}", name=f"Badge {n}") for n in range(5)))
        section = module.render_section("Muguett-DBY", badges)
        self.assertNotIn("<table", section)
        self.assertEqual(section.count('width="106" height="152"'), 5)
        self.assertEqual(section.count('tab=achievements">'), 6)

    def test_achievement_name_is_escaped_in_the_visible_label(self):
        badges = {"example": {"name": "A & B", "tier": "default", "source": "https://github.githubassets.com/assets/example.png"}}
        section = module.render_section("Muguett-DBY", badges)
        self.assertIn("A &amp; B, earned GitHub achievement", section)
        card = module.render_card(badges["example"], PNG)
        self.assertIn("A &amp; B", card)
        self.assertIn(">UNLOCKED</text>", card)
        ET.fromstring(card)

    def test_cached_image_is_reused_only_for_the_current_source(self):
        badge = {"name": "Pull Shark", "tier": "bronze", "source": "https://github.githubassets.com/assets/pull-shark-bronze-example.png"}
        card = module.render_card(badge, PNG)
        self.assertEqual(module.cached_png(card, badge["source"]), PNG)
        self.assertIsNone(module.cached_png(card, badge["source"].replace("bronze", "silver")))
        self.assertIsNone(module.cached_png("<not-an-svg", badge["source"]))

    def test_invalid_image_is_rejected(self):
        for data in (b"not a PNG", PNG[:16] + struct.pack(">II", 0, 64)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                module.validate_png(data)

    def test_existing_current_card_needs_no_image_download(self):
        badge = {"name": "Pull Shark", "tier": "bronze", "source": "https://github.githubassets.com/assets/pull-shark-bronze-example.png"}
        path = Path("fake-cards") / "pull-shark.svg"
        original = module.render_card(badge, PNG)
        with patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", return_value=original), patch.object(module, "fetch_png") as fetch:
            self.assertEqual(module.prepare_cards({"pull-shark": badge}, path.parent)[path], original)
            fetch.assert_not_called()

    def test_failed_image_fetch_does_not_write_partial_cards(self):
        badge = {"name": "Pull Shark", "tier": "bronze", "source": "https://github.githubassets.com/assets/pull-shark-bronze-example.png"}
        with patch.object(Path, "exists", return_value=False), patch.object(Path, "write_text") as write, patch.object(module, "fetch_png", side_effect=OSError("CDN unavailable")):
            with self.assertRaises(OSError):
                module.prepare_cards({"pull-shark": badge}, Path("fake-cards"))
            write.assert_not_called()

    def test_tier_upgrade_fetches_and_renders_the_new_badge(self):
        old = {"name": "Pull Shark", "tier": "bronze", "source": "https://github.githubassets.com/assets/pull-shark-bronze-example.png"}
        new = {**old, "tier": "silver", "source": old["source"].replace("bronze", "silver")}
        path = Path("fake-cards") / "pull-shark.svg"
        with patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", return_value=module.render_card(old, PNG)), patch.object(module, "fetch_png", return_value=PNG) as fetch:
            rendered = module.prepare_cards({"pull-shark": new}, path.parent)[path]
        fetch.assert_called_once_with(new["source"])
        self.assertIn(">SILVER</text>", rendered)
        self.assertEqual(module.cached_png(rendered, new["source"]), PNG)


if __name__ == "__main__":
    unittest.main()
