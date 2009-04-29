# spinystellate.py --- 
# 
# Filename: spinystellate.py
# Description: 
# Author: subhasis ray
# Maintainer: 
# Created: Wed Apr 29 10:24:37 2009 (+0530)
# Version: 
# Last-Updated: Thu Apr 30 02:49:54 2009 (+0530)
#           By: subhasis ray
#     Update #: 296
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# Initial version of a SpinyStellate cell implementation. Will
# refactor into a base class for Cell and then subclass here once I
# get the hang of the commonalities.
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
from collections import deque, defaultdict
import moose
from compartment import MyCompartment

class SpinyStellate(moose.Cell):
    #
    #     The dendritic structure is like this:
    #
    # level:    2  3  4  5   6  7   8    9
    #           c1-c2-c4-c7
    #            \
    #              c3-c5-c8
    #               \
    #                 c6-c9-c10-c11-c12-c13
    #
    # The compartments are numbered 1 to 13 and then we traverse the
    # tree in a breadth first manner.
    #
    # The following list captures the structure of the dendrites.
    # it is like:
    # subtree ::= [ node, child_subtree1, child_subtree2, child_subtree3, ...]
    dendritic_tree = [1, [2, [ 4, [7] ] ], 
                      [3, [5, [8]], 
                       [6, [9, [10, [11, [12, [13]]]]]]]]
    
    # radius in microns - the keys are the dendritic compartment
    # identities in dendritic_tree
    radius = {0: 7.5, # soma - actually this will be compartment no. 1
	      1: 1.06, 
	      2: 0.666666667,
	      3: 0.666666667, 
	      4: 0.666666667, 
	      5: 0.418972332, 
	      6: 0.418972332, 
	      7: 0.666666667, 
	      8: 0.418972332, 
	      9: 0.418972332, 
	      10: 0.418972332, 
	      11: 0.418972332, 
	      12: 0.418972332, 
	      13: 0.418972332} 
    
    channel_density = {0: {'NaF2':     4000.0,
                           'KDR_FS':   4000.0,
                           'KA':       20.0,
                           'K2':       1.0},

                       1: {'NaF2':     1500.0,
                           'NaPF_SS':  1.5,
                           'KDR_FS':   1000.0,
                           'KC_FAST':  100.0,
                           'KA':       300.0,
                           'KM':       37.5,
                           'K2':       1.0,
                           'KAHP_SLOWER':      1.0,
                           'CaL':      5.0,
                           'CaT_A':    1.0,
                           'AR':       2.5},

                       2:{'NaF2':      750.0,
                          'NaPF_SS':   0.75,
                          'KDR_FS':    750.0,
                          'KC_FAST':   100.0,
                          'KA':        300.0,
                          'KM':        37.5,
                          'K2':        1.0,
                          'KAHP_SLOWER':       1.0,
                          'CaL':       5.0,
                          'CaT_A':     1.0,
                          'AR':        2.5},

                       3: {'NaF2':     750.0,
                           'NaPF_SS':  0.75,
                           'KDR_FS':   750.0,
                           'KC_FAST':  100.0,
                           'KA':       20.0,
                           'KM':       37.5,
                           'K2':       1.0,
                           'KAHP_SLOWER': 1.0,
                           'CaL':      5.0,
                           'CaT_A':    1.0,
                           'AR':       2.5},
                       
                       4: {'NaF2': 0.005 * 1e4,
                           'NaPF_SS': 5.E-06 * 1e4,
                           'KC_FAST': 0.01 * 1e4,
                           'KA': 0.002 * 1e4,
                           'KM': 0.00375 * 1e4,
                           'K2': 0.0001 * 1e4,
                           'KAHP_SLOWER': 0.0001 * 1e4,
                           'CaL': 0.0005 * 1e4,
                           'CaT_A': 0.0001 * 1e4,
                           'AR': 0.00025 * 1e4},
                       
                       5: {'NaF2': 0.005 * 1e4,
                           'NaPF_SS': 5.E-06 * 1e4,
                           'KA': 0.002 * 1e4,
                           'KM': 0.00375 * 1e4,
                           'K2': 0.0001 * 1e4,
                           'KAHP_SLOWER': 0.0001 * 1e4,
                           'CaL': 0.0005 * 1e4,
                           'CaT_A': 0.0001 * 1e4,
                           'AR': 0.00025 * 1e4},

                       6: {'NaF2': 0.005 * 1e4,
                           'NaPF_SS': 5.E-06 * 1e4,
                           'KA': 0.002 * 1e4,
                           'KM': 0.00375 * 1e4,
                           'K2': 0.0001 * 1e4,
                           'KAHP_SLOWER': 0.0001 * 1e4,
                           'CaL': 0.0005 * 1e4,
                           'CaT_A': 0.0001 * 1e4,
                           'AR': 0.00025 * 1e4},

                       7: {'NaF2': 0.005 * 1e4, 
                           'NaPF_SS': 5.E-06 * 1e4, 
                           'KA': 0.002 * 1e4, 
                           'KM': 0.00375 * 1e4, 
                           'K2': 0.0001 * 1e4, 
                           'KAHP_SLOWER': 0.0001 * 1e4, 
                           'CaL': 0.003 * 1e4, 
                           'CaT_A': 0.0001 * 1e4, 
                           'AR': 0.00025 * 1e4},

                       8: {'NaF2': 0.005 * 1e4, 
                           'NaPF_SS': 5.E-06 * 1e4, 
                           'KA': 0.002 * 1e4, 
                           'KM': 0.00375 * 1e4, 
                           'K2': 0.0001 * 1e4, 
                           'KAHP_SLOWER': 0.0001 * 1e4, 
                           'CaL': 0.003 * 1e4, 
                           'CaT_A': 0.0001 * 1e4, 
                           'AR': 0.00025 * 1e4},

                       9: {'NaF2': 0.005 * 1e4,
                           'NaPF_SS': 5.E-06 * 1e4,
                           'KA': 0.002 * 1e4,
                           'KM': 0.00375 * 1e4,
                           'K2': 0.0001 * 1e4,
                           'KAHP_SLOWER': 0.0001 * 1e4,
                           'CaL': 0.003 * 1e4,
                           'CaT_A': 0.0001 * 1e4,
                           'AR': 0.00025 * 1e4}}
    
    def __init__(self, *args):
	moose.Cell.__init__(self, *args)
	self.levels = defaultdict(set) # Python >= 2.5 
	self.soma_dendrites = set() # List of compartments that are not
				 # part of axon
	self.axon = set()
        self._create_cell()
        self._set_passiveprops()
        self._connect_axial(self.soma)
        self._insert_channels()
        self.soma.insertCaPool(5.2e-6 / 2e-10, 50e-3)
        for i in range(2, 10):
            for comp in self.levels[i]:
                comp.insertCaPool(5.2e-6 / 2e-10, 20e-3)
        

    def _create_dtree(self, name_prefix, parent, tree, level, default_length=40e-6, radius_dict=radius):
	"""Create the dendritic tree structure with compartments.

	Returns the root."""
        if not tree:
            return
        comp = MyCompartment(name_prefix + str(tree[0]), parent)
        comp.length = default_length
        comp.diameter = radius_dict[tree[0]] * 2e-6
        self.levels[level].add(comp)
        self.soma_dendrites.add(comp)
        for subtree in tree[1:]:
            self._create_dtree(name_prefix, comp, subtree, level+1, default_length, radius_dict)
        

    def _create_cell(self):
        """Create the compartmental structure and set the geometry."""
	if not hasattr(self, 'levels'):
	    self.levels = defaultdict(set)
	comp = MyCompartment('soma', self)
	comp.length = 20e-6
	comp.diameter = 7.5 * 2e-6
	self.soma = comp
	self.levels[1].add(comp)
        self.soma_dendrites.add(comp)
	for i in range(4):
	   self. _create_dtree('d_' + str(i) + '_', comp, SpinyStellate.dendritic_tree, 2)
        axon_radius = [0.7, 0.6, 0.5, 0.5, 0.5, 0.5]
        parent = comp
        for i in range(5, -1, -1):
            comp = MyCompartment('a_' + str(i), parent)
            comp.length = 50e-6
            comp.diameter = axon_radius[i] * 2e-6
            self.axon.add(comp)
            self.levels[0].add(comp)
            parent = comp

    def _set_passiveprops(self):
        """Set the passive properties of the cells."""
        for comp in self.soma_dendrites:
            comp.setSpecificCm(9e-3)
            comp.setSpecificRm(5.0)
            comp.setSpecificRa(2.5)
        for comp in self.axon:
            comp.setSpecificCm(9e-3)
            comp.setSpecificRm(0.1)
            comp.setSpecificRa(1.0)

    def _connect_axial(self, root):
        """Connect parent-child compartments via axial-raxial
        messages."""
        if hasattr(root, 'axial_connected'):
           return
        parent = moose.Neutral(root.parent)
        if parent.className == 'Compartment':
            root.connect('raxial', parent, 'axial')
        root.axial_connected = True
        
        for child in root.children():
            obj = moose.Neutral(child)
            if obj.className == 'Compartment':
                self._connect_axial(obj)

    def _insert_channels(self):
        for level in range(10):
            comp_set = self.levels[level]
            for comp in comp_set:
                for channel, density in SpinyStellate.channel_density[level].items():
                    comp.insertChannel(channel, density)


import pylab
import pymoose
from simulation import Simulation

if __name__ == '__main__':
    sim = Simulation()
    s = SpinyStellate('ss', sim.model)
    vm_table = s.soma.insertRecorder('Vm', sim.data)
    sim.schedule()
    sim.run(50e-3)
    sim.dump_data('data')
    pylab.plot(vm_table)
    pylab.show()
    
# 
# spinystellate.py ends here