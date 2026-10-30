import copy,unittest
from ppt_workflow.exhibits import compose_exhibit
class ExhibitTests(unittest.TestCase):
    def setUp(self):
        self.items=[{'title':'输入','body':'核对资料','output':'来源记录'},{'title':'产出','body':'检查结果','output':'验收记录'}]
        self.rect={'x':1,'y':2,'w':10,'h':3};self.theme={'font':'Microsoft YaHei','colors':{'ink':'162E3B','accent':'117A7E','muted':'526474'}}
    def build(self,kind='process'):return compose_exhibit(kind,'test-flow',self.items,self.rect,self.theme)
    def test_native_elements_and_stable_mapping(self):
        a=self.build();self.assertEqual(a,self.build());self.assertEqual(len(a),len({e['id'] for e in a}));self.assertTrue(all(e['type'] in ('text','line') and e['editability_requirement']=='native' for e in a))
    def test_process_connectors_have_arrow(self):self.assertTrue(next(e for e in self.build() if e['type']=='line')['arrow_end'])
    def test_comparison_has_separator_not_directional_causality(self):self.assertFalse(next(e for e in self.build('comparison') if e['type']=='line')['arrow_end'])
    def test_action_requires_observable_output(self):
        self.items[0].pop('output')
        with self.assertRaisesRegex(ValueError,'output'):self.build('action')
    def test_every_element_stays_in_declared_region(self):
        for kind in ('process','comparison','action'):
            for e in self.build(kind):
                r=e['rect'];self.assertGreaterEqual(r['x'],1);self.assertGreaterEqual(r['y'],2);self.assertLessEqual(r['x']+r['w'],11);self.assertLessEqual(r['y']+r['h'],5)
    def test_density_is_not_silently_shrunk(self):
        self.items[0]['body']='x'*37
        with self.assertRaisesRegex(ValueError,'capacity'):self.build()
    def test_nan_and_small_regions_rejected(self):
        self.rect['w']=float('nan')
        with self.assertRaises(ValueError):self.build()
        self.rect['w']=1
        with self.assertRaises(ValueError):self.build()
