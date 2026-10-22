"""Guard native-badge parsing against duplicates, unrelated images and failed fetches."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("refresh_achievements", Path(__file__).with_name("refresh-achievements.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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
        self.assertNotIn("Starstruck", section)


if __name__ == "__main__":
    unittest.main()
