import unittest
from ppt_workflow.theme_library import theme_bundle,theme_catalog
from ppt_workflow.asset_direction import validate_style
from ppt_workflow.stages import skill_route

class ThemeLibraryTests(unittest.TestCase):
    def test_consistent_recipe_and_asset_roles(self):
        for key in ('research-light','showcase-dark'):
            b=theme_bundle(key)
            validate_style(b['asset_style'])
            self.assertEqual(b['design_system']['colors'],b['asset_style']['colors'])
            self.assertEqual(b['design_system']['font'],'Microsoft YaHei')
            self.assertIn('image-chart',[v['key'] for v in b['design_system']['layouts']])
        self.assertNotEqual(theme_bundle('research-light')['design_system']['colors'],theme_bundle('showcase-dark')['design_system']['colors'])

    def test_catalog_and_ownership(self):
        self.assertEqual(len(theme_catalog()['themes']),2)
        for command in ('theme-catalog','theme-prepare'):
            self.assertEqual(skill_route(command)['skill'],'ppt-template')
        with self.assertRaises(ValueError):theme_bundle('../unrelated')

if __name__=='__main__':unittest.main()
