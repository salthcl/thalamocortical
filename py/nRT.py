# nRT.py --- 
# 
# Filename: nRT.py
# Description: 
# Author: subhasis ray
# Maintainer: 
# Created: Fri Oct 16 15:18:24 2009 (+0530)
# Version: 
# Last-Updated: Thu Sep  6 17:51:06 2012 (+0530)
#           By: subha
#     Update #: 96
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


class nRT(TraubCell):
    chan_params = {
        'ENa': 50e-3,
        'EK': -100e-3,
        'EAR': -40e-3,
        'ECa': 125e-3,
        'EGABA': -75e-3, # Sanchez-Vives et al. 1997 
        'TauCa': 20e-3,
        'X_AR': 0.0
    }
    num_comp = 59
    presyn = 59
    level = TraubCell.readlevels('nRT.levels')
    depth = None
    proto_file = 'nRT.p'
    prototype = TraubCell.read_proto(proto_file, "nRT", level_dict=level, depth_dict=depth, params=chan_params)
    ca_dep_chans = ['KAHP_SLOWER','KC']

    def __init__(self, *args):
        TraubCell.__init__(self, *args)
        moose.CaConc(self.soma.path + '/CaPool').tau = 50e-3
	
    def _topology(self):
        self.presyn = 59
        self.level[1].add(self.comp[1])
        for ii in range(2, 42, 13):
            self.level[2].add(self.comp[ii])
        for ii in range(3, 43, 13):
            self.level[3].add(self.comp[ii])
            self.level[3].add(self.comp[ii + 1])
        for ii in range(5, 45, 13):
            self.level[4].add(self.comp[ii])
            self.level[4].add(self.comp[ii + 1])
            self.level[4].add(self.comp[ii + 2])
        for ii in range(8, 47, 13):
            self.level[5].add(self.comp[ii])
            self.level[5].add(self.comp[ii + 1])
            self.level[5].add(self.comp[ii + 2])
        for ii in range(11, 51, 13):
            self.level[6].add(self.comp[ii])
            self.level[7].add(self.comp[ii + 1])
            self.level[8].add(self.comp[ii + 2])
            self.level[9].add(self.comp[ii + 3])
        for ii in range(54, 60):
            self.level[0].add(self.comp[ii])
    
    def _setup_passive(self):
        for comp in self.comp[1:]:
	    comp.initVm = -75e-3

    def _setup_channels(self):
        """Set up connections between compartment and channels, and Ca pool"""
	for comp in self.comp[1:]:
	    ca_pool = None
	    ca_dep_chans = []
	    ca_chans = []
	    for child in comp.children():
		obj = moose.Neutral(child)
		if obj.name == 'CaPool':
		    ca_pool = moose.CaConc(child)
		    ca_pool.tau = 20e-3
		else:
		    obj_class = obj.className
		    if obj_class == 'HHChannel':
			obj = moose.HHChannel(child)
                        gbar = obj.Gbar
			pyclass = eval(obj.name)
			if issubclass(pyclass, KChannel):
			    obj.Ek = -100e-3
			    if issubclass(pyclass, KCaChannel):
				ca_dep_chans.append(obj)
			elif issubclass(pyclass, NaChannel):
			    obj.Ek = 50e-3
			elif issubclass(pyclass, CaChannel):
			    obj.Ek = 125e-3
			    if issubclass(pyclass, CaL):
				ca_chans.append(obj)
			elif issubclass(pyclass, AR):
			    obj.Ek = -40e-3
                            obj.X = 0.0
	    if ca_pool:
		for channel in ca_chans:
		    channel.connect('IkSrc', ca_pool, 'current')
		    config.LOGGER.debug(comp.name + ':' + channel.name + ' connected to ' + ca_pool.name)
		for channel in ca_dep_chans:
		    channel.useConcentration = 1
		    ca_pool.connect("concSrc", channel, "concen")
		    config.LOGGER.debug(comp.name + ':' + ca_pool.name +' connected to ' + channel.name)



    @classmethod
    def test_single_cell(cls):
        """Simulates a single nRT cell and plots the Vm and [Ca2+]"""

        config.LOGGER.info("/**************************************************************************")
        config.LOGGER.info(" *")
        config.LOGGER.info(" * Simulating a single cell: %s" % (cls.__name__))
        config.LOGGER.info(" *")
        config.LOGGER.info(" **************************************************************************/")
        sim = Simulation(cls.__name__)
        mycell = nRT(nRT.prototype, sim.model.path + "/nRT")
        config.LOGGER.info('Created cell: %s' % (mycell.path))
        vm_table = mycell.comp[mycell.presyn].insertRecorder('Vm_nRT', 'Vm', sim.data)
        pulsegen = mycell.soma.insertPulseGen('pulsegen', sim.model, firstLevel=3e-10, firstDelay=100.0e-3, firstWidth=200e-3)
#         pulsegen1 = mycell.soma.insertPulseGen('pulsegen1', sim.model, firstLevel=3e-7, firstDelay=150e-3, firstWidth=10e-3)

        sim.schedule()
        if mycell.has_cycle():
            config.LOGGING.warning("WARNING!! CYCLE PRESENT IN CICRUIT.")
        t1 = datetime.now()
        sim.run(500e-3)
        t2 = datetime.now()
        delta = t2 - t1
        config.LOGGER.info('simulation time: %g'  % (delta.seconds + 1e-6 * delta.microseconds))
        sim.dump_data('data')
        mycell.dump_cell('nRT.txt')        
        if config.has_pylab:
            mus_vm = config.pylab.array(vm_table) * 1e3
            mus_t = linspace(0, sim.simtime*1e3, len(mus_vm))
            try:
                nrn_vm = config.pylab.loadtxt('../nrn/mydata/Vm_nRT.plot')
                print 'Here', nrn_vm.shape
                nrn_t = nrn_vm[:, 0]
                nrn_vm = nrn_vm[:, 1]
                config.pylab.plot(nrn_t, nrn_vm, 'y-', label='nrn vm')
            except IOError:
                pass
            print mus_vm.shape, mus_t.shape
            config.pylab.plot(mus_t, mus_vm, 'g-.', label='mus vm')
            config.pylab.legend()
            config.pylab.title('nRT')
            config.pylab.show()
        
        
# test main --
from simulation import Simulation
from subprocess import call
if __name__ == "__main__":
    # call(['nrngui', 'test_nRT.hoc'], cwd='../nrn')
    nRT.test_single_cell()




# 
# nRT.py ends here
