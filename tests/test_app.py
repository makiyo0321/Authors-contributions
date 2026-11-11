import unittest
import tkinter as tk
from unittest.mock import patch
import author_contributions as module

class AppTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        with patch.object(module.AuthorContributionsApp, 'load_custom_formats'):
            self.app = module.AuthorContributionsApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_pinyin(self):
        self.assertEqual(self.app.resolve_name('张绪霞', ''), 'Zhang Xuxia')
        self.assertEqual(self.app.resolve_name('欧阳娜娜', ''), 'Ouyang Nana')
        self.assertEqual(self.app.resolve_name('张绪霞', 'Xuxia Zhang'), 'Xuxia Zhang')

    def test_language_and_assignments(self):
        self.app.full_entry.insert(0, 'Madonna')
        self.app.add_author()
        self.app.role_vars['Conceptualization']['Madonna'].set(True)
        for language, heading in [('English', 'CRediT roles'), ('中文', 'CRediT角色')]:
            self.app.language.set(language)
            self.app.apply_language()
            self.assertEqual(self.app.tree.heading('角色')['text'], heading)
            self.assertTrue(self.app.role_vars['Conceptualization']['Madonna'].get())
        self.app.format_var.set('npj Digital Medicine')
        self.app.generate_contributions()
        self.assertIn('M.: Conceptualization.', self.app.output_text.get('1.0', 'end'))

    def test_template_validation(self):
        for template in ['{bad}', '{authors.__class__}: {role}', '{authors']:
            with self.assertRaises(ValueError):
                self.app.validate_template(template)

if __name__ == '__main__':
    unittest.main()
