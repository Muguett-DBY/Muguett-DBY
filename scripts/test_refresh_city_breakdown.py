"""Checks for the activity values displayed alongside the contribution city."""

import unittest
import xml.etree.ElementTree as ET

from refresh_city_breakdown import END, START, extract_counts, render_block, replace_block


def radar_xml(axes: str) -> ET.Element:
    return ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{axes}</svg>')


class CityBreakdownTests(unittest.TestCase):
    def setUp(self):
        self.axes = "".join(
            f'<g class="axis"><text>{name}<title>{value}</title></text></g>'
            for name, value in (("Commit", 1234), ("Issue", 0), ("PullReq", 12),
                                ("Review", 8), ("Repo", 3))
        )

    def test_reads_and_formats_each_actual_radar_value(self):
        counts = extract_counts(radar_xml(self.axes))
        self.assertEqual(counts, {"Commit": 1234, "Issue": 0, "PullReq": 12,
                                  "Review": 8, "Repo": 3})
        block = render_block(counts)
        self.assertIn("<strong>1,234</strong>&nbsp;commits", block)
        self.assertIn("<strong>0</strong>&nbsp;issues&nbsp;opened", block)
        self.assertIn("<strong>3</strong>&nbsp;repos&nbsp;created", block)

    def test_missing_duplicate_or_nonnumeric_values_are_rejected(self):
        for axes in (self.axes.replace('<g class="axis"><text>Repo<title>3</title></text></g>', ''),
                     self.axes + '<g class="axis"><text>Repo<title>4</title></text></g>',
                     self.axes.replace('<title>8</title>', '<title>unknown</title>')):
            with self.subTest(axes=axes), self.assertRaises(ValueError):
                extract_counts(radar_xml(axes))
        self.assertIn("unavailable", render_block(None))

    def test_only_the_marked_block_is_replaced(self):
        before = f"before\n{START}\nold\n{END}\nafter\n"
        result = replace_block(before, render_block(extract_counts(radar_xml(self.axes))))
        self.assertTrue(result.startswith("before\n"))
        self.assertTrue(result.endswith("\nafter\n"))
        self.assertEqual(replace_block(result, render_block(extract_counts(radar_xml(self.axes)))), result)
        for bad in ("no markers", before + before, f"{END}\n{START}"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                replace_block(bad, render_block(None))


if __name__ == "__main__":
    unittest.main()
