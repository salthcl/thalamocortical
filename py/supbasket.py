# supbasket.py --- 
# 
# Filename: supbasket.py
# Description: Superficial Layer 2/3 basket cells
# Author: subhasis ray
# Maintainer: 
# Created: Tue Oct  6 16:52:28 2009 (+0530)
# Version: 
# Last-Updated: Wed Dec 14 11:06:39 2011 (+0530)
#           By: Subhasis Ray
#     Update #: 52
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
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
# 
# 

# Code:

from datetime import datetime
import config
import trbutil
import moose
from cell import *
from capool import CaPool

class SupBasket(TraubCell):
    chan_params = {
        'ENa': 50e-3,
        'EK': -100e-3,
        'EAR': -40e-3,
        'ECa': 125e-3,
        'EGABA': -75e-3, # Sanchez-Vives et al. 1997 
        'TauCa': 20e-3,
        'X_AR': 0.0
        }

    ca_dep_chans = ['KC_FAST']
    num_comp = 59
    presyn = 59
    # level maps level number to the set of compartments belonging to it
    level = TraubCell.readlevels("SupBasket.levels")
    # depth stores a map between level number and the depth of the compartments.
    depth = None    

    proto_file = 'SupBasket.p'
    prototype = TraubCell.read_proto(proto_file, 'SupBasket', level_dict=level, depth_dict=depth, params=chan_params)
    def __init__(self, *args):
        # start = datetime.now()
        TraubCell.__init__(self, *args)
        soma_ca_pool = moose.CaConc(self.soma.path + '/CaPool')
        soma_ca_pool.tau = 50e-3
        # end = datetime.now()
        # delta = end - start
        # config.BENCHMARK_LOGGER.info('created cell in: %g s' % (delta.days * 86400 + delta.seconds + delta.microseconds * 1e-6))
	
    def _topology(self):
        raise Exception, 'Deprecated'
	
    def _setup_passive(self):
        raise Exception, 'Deprecated'

    def _setup_channels(self):
        raise Exception, 'Depreacted'

    @classmethod
    def test_single_cell(cls):
        """Simulates a single nRT cell and plots the Vm and [Ca2+]"""

        config.LOGGER.info("/**************************************************************************")
        config.LOGGER.info(" *")
        config.LOGGER.info(" * Simulating a single cell: %s" % (cls.__name__))
        config.LOGGER.info(" *")
        config.LOGGER.info(" **************************************************************************/")
        sim = Simulation(cls.__name__)
        mycell = SupBasket(SupBasket.prototype, sim.model.path + "/SupBasket")
        print 'Created cell:', mycell.path
        vm_table = mycell.comp[mycell.presyn].insertRecorder('Vm_supbask', 'Vm', sim.data)
        pulsegen = mycell.soma.insertPulseGen('pulsegen', sim.model, firstLevel=3e-10, firstDelay=100e-3, firstWidth=200e-3)
#         pulsegen1 = mycell.soma.insertPulseGen('pulsegen1', sim.model, firstLevel=3e-7, firstDelay=150e-3, firstWidth=10e-3)

        sim.schedule()
        if mycell.has_cycle():
            print "WARNING!! CYCLE PRESENT IN CICRUIT."
        t1 = datetime.now()
        sim.run(500e-3)
        t2 = datetime.now()
        delta = t2 - t1
        print 'simulation time: ', delta.seconds + 1e-6 * delta.microseconds
        sim.dump_data('data')
        mycell.dump_cell('supbask.txt')
        if config.has_pylab:
            mus_vm = config.pylab.array(vm_table) * 1e3
            nrn_vm = config.pylab.loadtxt('../nrn/mydata/Vm_supbask.plot')
            nrn_t = nrn_vm[:, 0]
            mus_t = linspace(0, nrn_t[-1], len(mus_vm))
            nrn_vm = nrn_vm[:, 1]
            nrn_ca = config.pylab.loadtxt('../nrn/mydata/Ca_supbask.plot')
            nrn_ca = nrn_ca[:,1]
            config.pylab.plot(nrn_t, nrn_vm, 'y-', label='nrn vm')
            config.pylab.plot(mus_t, mus_vm, 'g-.', label='mus vm')
    #         if ca_table:
    #             ca_array = config.pylab.array(ca_table)
    #             config.pylab.plot(nrn_t, -nrn_ca, 'r-', label='nrn (-)ca')
    #             config.pylab.plot(mus_t, -ca_array, 'b-.', label='mus (-)ca')
    #             print config.pylab.amax(ca_table)
            config.pylab.legend()
            config.pylab.title('supbasket')
            config.pylab.show()
        
        
# test main --
from simulation import Simulation
from subprocess import call
if __name__ == "__main__":
#     call(['/home/subha/neuron/nrn/x86_64/bin/nrngui', 'test_supbask.hoc'], cwd='../nrn')
    SupBasket.test_single_cell()
    


# 
# supbasket.py ends here
