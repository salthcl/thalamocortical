# spinystellate.py --- 
# 
# Filename: spinystellate.py
# Description: 
# Author: subhasis ray
# Maintainer: 
# Created: Tue Sep 29 11:43:22 2009 (+0530)
# Version: 
# Last-Updated: Wed Apr 21 11:18:00 2010 (+0530)
#           By: Subhasis Ray
#     Update #: 421
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# 
# 
# 

# Change log:
# 
# 
# 
# Code:

from datetime import datetime
import config
import trbutil
import moose
from cell import *
from capool import CaPool
# from cellview import MyCellView

class SpinyStellate(TraubCell):
    chan_params = {
        'ENa': 50e-3,
        'EK': -100e-3,
        'EAR': -40e-3,
        'ECa': 100e-3,
        'EGABA': -75e-3, # Sanchez-Vives et al. 1997 
        'TauCa': 20e-3,
        'X_AR': 0.0
        }
    ca_dep_chans = ['KAHP_SLOWER', 'KC_FAST']
    presyn = 57
    num_comp = 59
    proto_file = 'SpinyStellate.p'
    prototype = TraubCell.read_proto("SpinyStellate.p", "SpinyStellate", chan_params)
    def __init__(self, *args):
	TraubCell.__init__(self, *args)
        soma_ca_pool = moose.CaConc(self.soma.path + '/CaPool')
        soma_ca_pool.tau = 50e-3

    def _topology(self):
        raise Exception, 'Deprecated method.'

    def _setup_passive(self):
        raise Exception, 'Deprecated. All passive properties including initVm and Em are set in .p file.'
    

    def _setup_channels(self):
        """Set up connection between CaPool, Ca channels, Ca dependnet channels."""
        raise Exception, 'Deprecated.'

    @classmethod
    def test_single_cell(cls):
        """Simulates a single spiny stellate cell and plots the Vm and
        [Ca2+]"""

        config.LOGGER.info("/**************************************************************************")
        config.LOGGER.info(" *")
        config.LOGGER.info(" * Simulating a single cell: %s" % (cls.__name__))
        config.LOGGER.info(" *")
        config.LOGGER.info(" **************************************************************************/")
        sim = Simulation(cls.__name__)
        mycell = SpinyStellate(sim.model.path + "/SpinyStellate", SpinyStellate.proto_file)
        for handler in config.LOGGER.handlers:
            handler.flush()


        mycell.soma.x0 = 0.0
        mycell.soma.y0 = 0.0
        mycell.soma.z0 = 0.0
        mycell.soma.x = 0.0
        mycell.soma.y = 0.0
        mycell.soma.z = mycell.soma.length
        # mycellview = MyCellView(mycell)
        config.LOGGER.debug('Created cell: %s' % (mycell.path))
        # for neighbour in mycell.soma.neighbours('raxial'):
        #     print 'RAXIAL', neighbours.path()
        # for neighbour in mycell.soma.neighbours('axial'):
        #     print 'AXIAL', neighbour.path()
        vm_table = mycell.comp[mycell.presyn].insertRecorder('Vm_spinstell', 'Vm', sim.data)
        pulsegen = mycell.soma.insertPulseGen('pulsegen', sim.model, firstLevel=3e-10, firstDelay=50e-3, firstWidth=50e-3)
#         pulsegen1 = mycell.soma.insertPulseGen('pulsegen1', sim.model, firstLevel=3e-7, firstDelay=150e-3, firstWidth=10e-3)

        sim.schedule()
        if mycell.has_cycle():
            print "WARNING!! CYCLE PRESENT IN CICRUIT."
        t1 = datetime.now()
        sim.run(200e-3)
        t2 = datetime.now()
        delta = t2 - t1
        print 'simulation time: ', delta.seconds + 1e-6 * delta.microseconds
        # sim.dump_data('data')
        # mycell.dump_cell('spinstell.txt')
        
        mus_vm = pylab.array(vm_table) * 1e3
        nrn_vm = pylab.loadtxt('../nrn/mydata/Vm_spinstell.plot')
        nrn_t = nrn_vm[:, 0]
        mus_t = linspace(0, nrn_t[-1], len(mus_vm))
        nrn_vm = nrn_vm[:, 1]
        nrn_ca = pylab.loadtxt('../nrn/mydata/Ca_spinstell.plot')
        nrn_ca = nrn_ca[:,1]
        pylab.plot(nrn_t, nrn_vm, 'y-', label='nrn vm')
        pylab.plot(mus_t, mus_vm, 'g-.', label='mus vm')
#         if ca_table:
#             ca_array = pylab.array(ca_table)
#             pylab.plot(nrn_t, -nrn_ca, 'r-', label='nrn (-)ca')
#             pylab.plot(mus_t, -ca_array, 'b-.', label='mus (-)ca')
#             print pylab.amax(ca_table)
        pylab.legend()
        pylab.show()

import unittest

class SpinyStellateTestCase(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation('SpinyStellate')
        path = self.sim.model.path + '/' + 'TestSpinyStellate'
        config.LOGGER.debug('Creating cell %s' % (path))
        TraubCell.adjust_chanlib(SpinyStellate.chan_params)
        self.cell = SpinyStellate(path, SpinyStellate.proto_file)
        config.LOGGER.debug('Cell created')
        for handler in config.LOGGER.handlers:
            handler.flush()
        self.sim.schedule()

    def test_compartment_count(self):
        for comp_no in range(SpinyStellate.num_comp):
            path = '%s/comp_%d' % (self.cell.path, comp_no + 1)
            self.assertTrue(config.context.exists(path))
    
    def test_initVm(self):
        for comp_no in range(SpinyStellate.num_comp):
            self.assertAlmostEqual(self.cell.comp[comp_no + 1].initVm, -65e-3)

    def test_Em(self):
        for comp_no in range(SpinyStellate.num_comp):
            self.assertAlmostEqual(self.cell.comp[comp_no + 1].Em, -65e-3)

    def test_Ca_connections(self):
        for comp_no in range(SpinyStellate.num_comp):
            ca_path = self.cell.comp[comp_no + 1].path + '/CaPool'
            if not config.context.exists(ca_path):
                continue
            caPool = moose.CaConc(ca_path)
            for chan in SpinyStellate.ca_dep_chans:
                pass
            sources = caPool.neighbours('current')
            self.failIfEqual(len(src), 0)
            for chan in sources:
                self.assertTrue(chan.path().endswith('CaL'))
                    
    def test_reversal_potentials(self):
        for num in range(SpinyStellate.num_comp):
            comp = self.cell.comp[num + 1]
            for chan_id in comp.neighbours('channel'):
                chan = moose.HHChannel(chan_id)
                chan_class = eval(chan.name)
                key = None
                if issubclass(chan_class, NaChannel):
                    key = 'ENa'
                elif issubclass(chan_class, KChannel):
                    key = 'EK'
                elif issubclass(chan_class, CaChannel):
                    key = 'ECa'
                elif issubclass(chan_class, AR):
                    key = 'EAR'
                else:
                    pass
                self.assertAlmostEqual(chan.Ek, SpinyStellate.chan_params[key])
                    
                

# test main --
from simulation import Simulation
import pylab
from subprocess import call
if __name__ == "__main__":
#     call(['/home/subha/neuron/nrn/x86_64/bin/nrngui', 'test_spinstell.hoc'], cwd='../nrn')
    SpinyStellate.test_single_cell()
    # unittest.main()


# 
# spinystellate.py ends here
