# tuftedIB.py --- 
# 
# Filename: tuftedIB.py
# Description: 
# Author: subhasis ray
# Maintainer: 
# Created: Fri Oct 16 11:44:48 2009 (+0530)
# Version: 
# Last-Updated: Wed Feb 17 17:27:21 2010 (+0530)
#           By: Subhasis Ray
#     Update #: 22
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


class TuftedIB(TraubCell):
    prototype = TraubCell.read_proto("TuftedIB.p", "TuftedIB")
    ca_dep_chans = ['KAHP','KAHP_SLOWER', 'KAHP_DP', 'KC', 'KC_FAST']
    def __init__(self, *args):
	TraubCell.__init__(self, *args)
	
    def _topology(self):
        self.presyn = 60
    
    def _setup_passive(self):
        for comp in self.comp[1:]:
	    comp.initVm = -70e-3

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
		    ca_pool.tau = 1e-3/0.075
		else:
		    obj_class = obj.className
		    if obj_class == 'HHChannel':
			obj = moose.HHChannel(child)
#                         if not obj.name in self.chan_list:
#                             obj.Gbar = 0.0
			pyclass = eval(obj.name)
			if issubclass(pyclass, KChannel):
			    obj.Ek = -95e-3
			    if issubclass(pyclass, KCaChannel):
				ca_dep_chans.append(obj)
			elif issubclass(pyclass, NaChannel):
			    obj.Ek = 50e-3
			elif issubclass(pyclass, CaChannel):
			    obj.Ek = 125e-3
			    if issubclass(pyclass, CaL):
				ca_chans.append(obj)
			elif issubclass(pyclass, AR):
			    obj.Ek = -35e-3
	    if ca_pool:
		for channel in ca_chans:
		    channel.connect('IkSrc', ca_pool, 'current')
		    print comp.name, ':', channel.name, 'connected to', ca_pool.name
		for channel in ca_dep_chans:
		    channel.useConcentration = 1
		    ca_pool.connect("concSrc", channel, "concen")
		    print comp.name, ':', ca_pool.name, 'connected to', channel.name

	obj = moose.CaConc(self.soma.path + '/CaPool')
        obj.tau = 100e-3
	# Special case: individually specified beta_cad's in level  2
	moose.CaConc(self.comp[2].path + '/CaPool').tau  =   1e-3/0.02
        moose.CaConc(self.comp[ 3].path + '/CaPool' ).tau = 1e-3 /  0.075
        moose.CaConc(self.comp[ 4].path + '/CaPool' ).tau = 1e-3 /  0.075
        moose.CaConc(self.comp[ 5].path + '/CaPool' ).tau = 1e-3 /  0.02
        moose.CaConc(self.comp[ 6].path + '/CaPool' ).tau = 1e-3 /  0.02
        moose.CaConc(self.comp[ 7].path + '/CaPool' ).tau = 1e-3 /  0.075
        moose.CaConc(self.comp[ 8].path + '/CaPool' ).tau = 1e-3 /  0.075
        moose.CaConc(self.comp[ 9].path + '/CaPool' ).tau = 1e-3 /  0.075
        moose.CaConc(self.comp[ 10].path + '/CaPool' ).tau = 1e-3 / 0.075
        moose.CaConc(self.comp[ 11].path + '/CaPool' ).tau = 1e-3 / 0.075
        moose.CaConc(self.comp[ 12].path + '/CaPool' ).tau = 1e-3 / 0.075


    @classmethod
    def test_single_cell(cls):
        """Simulates a single tufted intrinsically bursting cell and
        plots the Vm and [Ca2+]"""

        config.LOGGER.info("/**************************************************************************")
        config.LOGGER.info(" *")
        config.LOGGER.info(" * Simulating a single cell: %s" % (cls.__name__))
        config.LOGGER.info(" *")
        config.LOGGER.info(" **************************************************************************/")
        sim = Simulation(cls.__name__)
        mycell = TuftedIB(TuftedIB.prototype, sim.model.path + "/TuftedIB")
        print 'Created cell:', mycell.path
        vm_table = mycell.comp[mycell.presyn].insertRecorder('Vm_tuftIB', 'Vm', sim.data)
        ca_conc_path = mycell.soma.path + '/CaPool'
        ca_table = None
        if config.context.exists(ca_conc_path):
            ca_conc = moose.CaConc(ca_conc_path)
            ca_table = moose.Table('Ca_tuftIB', sim.data)
            ca_table.stepMode = 3
            ca_conc.connect('Ca', ca_table, 'inputRequest')
        kc_path = mycell.soma.path + '/KC'
        gk_table = None
        if config.context.exists(kc_path):
            gk_table = moose.Table('gkc', sim.data)
            gk_table.stepMode = 3
            kc = moose.HHChannel(kc_path)
            kc.connect('Gk', gk_table, 'inputRequest')
            pymoose.showmsg(ca_conc)
        pulsegen = mycell.soma.insertPulseGen('pulsegen', sim.model, firstLevel=0.3e-9, firstDelay=0.0, firstWidth=50e-3)
#         pulsegen1 = mycell.soma.insertPulseGen('pulsegen1', sim.model, firstLevel=3e-7, firstDelay=150e-3, firstWidth=10e-3)

        sim.schedule()
        if mycell.has_cycle():
            print "WARNING!! CYCLE PRESENT IN CICRUIT."
        t1 = datetime.now()
        sim.run(200e-3)
        t2 = datetime.now()
        delta = t2 - t1
        print 'simulation time: ', delta.seconds + 1e-6 * delta.microseconds
        sim.dump_data('data')
        mycell.dump_cell('tuftIB.txt')
        
        mus_vm = pylab.array(vm_table) * 1e3
        nrn_vm = pylab.loadtxt('../nrn/mydata/Vm_tuftIB.plot')
        nrn_t = nrn_vm[:, 0]
        mus_t = linspace(0, nrn_t[-1], len(mus_vm))
        nrn_vm = nrn_vm[:, 1]
        nrn_ca = pylab.loadtxt('../nrn/mydata/Ca_tuftIB.plot')
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
        
        
# test main --
from simulation import Simulation
import pylab
from subprocess import call
if __name__ == "__main__":
    call(['/home/subha/neuron/nrn/x86_64/bin/nrngui', 'test_tuftIB.hoc'], cwd='../nrn')
    TuftedIB.test_single_cell()



# 
# tuftedIB.py ends here
