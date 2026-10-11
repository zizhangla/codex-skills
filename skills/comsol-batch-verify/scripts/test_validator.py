"""Local negative controls for the result gate. Does not launch COMSOL."""
import json, unittest
from smoke_test import validate

def payload(**changes):
    data=dict(integral_u=.5,area=1.,squared_error_integral=0.)
    data.update(changes)
    return 'COMSOL_SMOKE_RESULT='+json.dumps(data)+'\nCOMSOL_SMOKE_DONE\n'

class Gate(unittest.TestCase):
    def test_analytic_result(self): self.assertEqual(validate(payload())['integral_u'],.5)
    def test_reject_false_success(self):
        cases=[payload().replace('COMSOL_SMOKE_DONE',''),payload()+payload(),
               payload(integral_u=.6),payload(area=2.),payload(squared_error_integral=-1.),
               payload(squared_error_integral=1e-8),payload(integral_u=float('nan')),
               payload(area=True),payload(extra=1),payload().replace('RESULT={','RESULT={bad')]
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaises((ValueError,TypeError)): validate(text)

if __name__=='__main__': unittest.main()
