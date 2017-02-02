import unittest
import copy
from astropy.io import fits

import numpy as np
from hipercam import Window, Windat, HipercamError

class TestWindat(unittest.TestCase):
    """Provides simple tests of almost every Windat method and attribute. If any
    of these fail, something is badly wrong.

    """

    def setUp(self):

        # build some (small) Windats
        self.win1 = Window(31,41,3,4,1,2)
        self.data1 = np.ones((self.win1.ny,self.win1.nx))
        self.wind1 = Windat(self.win1, self.data1)

        # should be compatible with win1
        self.wind2 = copy.deepcopy(self.wind1)

        # designed to be incompatible with win1
        self.wind3 = copy.deepcopy(self.wind1)
        self.wind3.llx += 1

    def test_windat_size(self):
        self.assertEqual(self.wind1.size, self.win1.nx*self.win1.ny,
                         'incorrect number of pixels returned')

    def test_windat_win(self):
        self.assertEqual(self.wind1.win, self.win1,
                         'incorrect Window returned')

    def test_windat_set_const(self):
        self.wind3.set_const(10.)
        self.assertEqual(self.wind3.data[0,0],10.,
                         'incorrect value returned')

    def test_windat_add_noise(self):
        """Rather crude test this, but it should pick up disasters"""
        win = Window(1,1,100,100,1,1)
        data = np.zeros((win.ny,win.nx))
        wind = Windat(win, data)

        wind.add_noise(1.,1.)
        mean = wind.mean()
        std = wind.std()
        npix = wind.size

        self.assertTrue(abs(mean) < 7./np.sqrt(npix),
                        'mean out of expected range')
        self.assertTrue(abs(std - 1.) < 7./np.sqrt(2*np.sqrt(npix)),
                        'standard deviation out of expected range')

    def test_windat_whdu(self):
        hdu = self.wind1.whdu()
        self.assertIsInstance(hdu,fits.ImageHDU)
        head = hdu.header
        self.assertTrue('LLX' in head, 'LLX not found in HDU')
        self.assertTrue('LLY' in head, 'LLX not found in HDU')
        self.assertTrue('XBIN' in head, 'LLX not found in HDU')
        self.assertTrue('YBIN' in head, 'LLX not found in HDU')

    def test_windat_rhdu(self):
        # writes to and then reads from an HDU
        hdu = self.wind1.whdu()
        wind = Windat.rhdu(hdu)
        self.assertEqual(wind, self.wind1,
                         'recovered Windat differs from original format')
        self.assertTrue((wind.data == self.wind1.data).all(),
                         'recovered Windat differs from original data')

    def test_windat_min(self):
        self.wind3.set_const(0.)
        self.wind3.data[0,0] = -1.
        self.assertEqual(self.wind3.min(), -1.,
                         'incorrect minimum returned')

    def test_windat_max(self):
        self.wind3.set_const(0.)
        self.wind3.data[0,0] = 1.
        self.assertEqual(self.wind3.max(), 1.,
                         'incorrect maxiumum returned')

    def test_windat_mean(self):
        self.wind3.set_const(0.)
        self.wind3.data[0,0] = 1.
        self.wind3.data[0,1] = -1.
        self.assertEqual(self.wind3.mean(), 0.,
                         'incorrect mean returned')

    def test_windat_std(self):
        win = Window(1,1,2,2,1,1)
        data = np.array([[-1.,-1.],[1.,1.]])
        wind = Windat(win, data)
        self.assertEqual(wind.std(), 1.,
                         'incorrect standard deviation returned')

    def test_windat_percentile(self):
        win = Window(1,1,3,3,1,1)
        data = np.array([[-1.,-1.,-1.],[-1.,0.,1.],[1.,1.,1.]])
        wind = Windat(win, data)
        self.assertEqual(wind.percentile(50.), 0.,
                         'incorrect percentile value returned')

    def test_windat_iadd(self):
        self.wind3.set_const(1.)
        self.wind3 += 1.
        self.assertEqual(self.wind3.data[0,0],2.,
                         'in place addition of constant failed')
        self.wind3 += self.wind3
        self.assertEqual(self.wind3.data[0,0],4.,
                         'in place addition of Windat failed')

    def test_windat_isub(self):
        self.wind3.set_const(10.)
        self.wind3 -= 1.
        self.assertEqual(self.wind3.data[0,0],9.,
                         'in place subtraction of constant failed')
        self.wind3 -= self.wind3
        self.assertEqual(self.wind3.data[0,0],0.,
                         'in place subtraction of Windat failed')

    def test_windat_imul(self):
        self.wind3.set_const(10.)
        self.wind3 *= 2.
        self.assertEqual(self.wind3.data[0,0],20.,
                         'in place multiplcation by constant failed')
        self.wind3 *= self.wind3
        self.assertEqual(self.wind3.data[0,0],400.,
                         'in place multiplcation by Windat failed')

    def test_windat_itruediv(self):
        self.wind3.set_const(21.)
        self.wind3 /= 2.
        self.assertEqual(self.wind3.data[0,0],10.5,
                         'in place division by constant failed')
        self.wind3 /= self.wind3
        self.assertEqual(self.wind3.data[0,0],1.,
                         'in place division by Windat failed')

    def test_windat_add(self):
        self.wind3.set_const(1.)
        self.wind3 = self.wind3 + 1.
        self.assertEqual(self.wind3.data[0,0],2.,
                         'addition of constant failed')
        self.wind3 = self.wind3 + self.wind3
        self.assertEqual(self.wind3.data[0,0],4.,
                         'addition of Windat failed')

    def test_windat_sub(self):
        self.wind3.set_const(10.)
        self.wind3 = self.wind3 -  1.
        self.assertEqual(self.wind3.data[0,0],9.,
                         'subtraction of constant failed')
        self.wind3 = self.wind3 - self.wind3
        self.assertEqual(self.wind3.data[0,0],0.,
                         'subtraction of Windat failed')

    def test_windat_mul(self):
        self.wind3.set_const(2.)
        self.wind3 = self.wind3 *  2.
        self.assertEqual(self.wind3.data[0,0],4.,
                         'multiplication by constant failed')
        self.wind3 = self.wind3 * self.wind3
        self.assertEqual(self.wind3.data[0,0],16.,
                         'multiplication by Windat failed')

    def test_windat_truediv(self):
        self.wind3.set_const(6.)
        self.wind3 = self.wind3 /  2.
        self.assertEqual(self.wind3.data[0,0],3.,
                         'division by constant failed')
        self.wind3 = self.wind3 / self.wind3
        self.assertEqual(self.wind3.data[0,0],1.,
                         'division by Windat failed')

    def test_windat_radd(self):
        self.wind3.set_const(1.)
        self.wind3 = 1. + self.wind3
        self.assertEqual(self.wind3.data[0,0],2.,
                         'addition to a constant failed')

    def test_windat_rsub(self):
        self.wind3.set_const(1.)
        self.wind3 = 10. - self.wind3
        self.assertEqual(self.wind3.data[0,0],9.,
                         'subtraction from a constant failed')

    def test_windat_rmul(self):
        self.wind3.set_const(2.)
        self.wind3 = 10. * self.wind3
        self.assertEqual(self.wind3.data[0,0],20.,
                         'multiplication of a constant failed')

    def test_windat_rtruediv(self):
        self.wind3.set_const(2.)
        self.wind3 = 10. / self.wind3
        self.assertEqual(self.wind3.data[0,0],5.,
                         'division of a constant failed')

if __name__ == '__main__':
    unittest.main()
