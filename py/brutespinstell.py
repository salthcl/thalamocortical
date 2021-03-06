#!/usr/bin/env python
# brutespinstell.py --- 
# 
# Filename: brutespinstell.py
# Description: This is an unelegant version of spiny stellate cells
# Author: subhasis ray
# Maintainer: 
# Created: Fri May  8 11:24:30 2009 (+0530)
# Version: 
# Last-Updated: Fri Sep 11 02:46:05 2009 (+0530)
#           By: subhasis ray
#     Update #: 568
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

# Code:

from collections import deque, defaultdict
from datetime import datetime
import cell
from kchans import *
from nachans import *
from cachans import *
from capool import *
from archan import *

from compartment import *

class SpinyStellate(cell.TraubCell):
    ENa = 50e-3
    EK = -100e-3
    ECa = 125e-3
    Em = -65e-3
    EAR = -40e-3
    conductance = {
	0: {
	    'NaF2':   0.4,
	    'KDR_FS':   0.4,
	    'KA':   0.002,
	    'K2':   0.0001
	    },
	1: {
	    'NaF2':   0.15,
	    'NaPF_SS':   0.00015,
	    'KDR_FS':   0.1,
	    'KC_FAST':   0.01,
	    'KA':   0.03,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	2: {
	    'NaF2':   0.075,
	    'NaPF_SS':   7.5E-05,
	    'KDR_FS':   0.075,
	    'KC_FAST':   0.01,
	    'KA':   0.03,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	3: {
	    'NaF2':   0.075,
	    'NaPF_SS':   7.5E-05,
	    'KDR_FS':   0.075,
	    'KC_FAST':   0.01,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	4: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KC_FAST':   0.01,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	5: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	6: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.0005,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	7: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.003,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	8: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.003,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    },
	9: {
	    'NaF2':   0.005,
	    'NaPF_SS':   5.E-06,
	    'KA':   0.002,
	    'KM':   0.00375,
	    'K2':   0.0001,
	    'KAHP_SLOWER':   0.0001,
	    'CaL':   0.003,
	    'CaT_A':   0.0001,
	    'AR':   0.00025
	    }
	}

    channels = {'NaF2': 'NaF2_SS', 
                'NaPF_SS': 'NaPF_SS',
                'KDR_FS': 'KDR_FS',
                'KA': 'KA', 
                'K2': 'K2', 
                'KM': 'KM', 
                'KC_FAST': 'KC_FAST', 
                'KAHP_SLOWER': 'KAHP_SLOWER',
                'CaL': 'CaL', 
                'CaT_A': 'CaT_A', 
                'AR': 'AR'}

    channel_lib = {}
    channel_lib['NaF2'] = NaF2('NaF2_SS', config.lib, shift=-2.5e-3)
    channel_lib['NaPF_SS'] = NaPF_SS('NaPF_SS', config.lib, shift=-2.5e-3)
    channel_lib['KDR_FS'] = KDR_FS('KDR_FS', config.lib)
    channel_lib['KA'] = KA('KA', config.lib)
    channel_lib['K2'] = K2('K2', config.lib)
    channel_lib['KM'] = KM('KM', config.lib)
    channel_lib['KC_FAST'] = KC_FAST('KC_FAST', config.lib)
    channel_lib['KAHP_SLOWER'] = KAHP_SLOWER('KAHP_SLOWER', config.lib)
    channel_lib['CaL'] = CaL('CaL', config.lib)
    channel_lib['CaT_A'] = CaT_A('CaT_A', config.lib)
    channel_lib['AR'] = AR('AR', config.lib)

    
    def __init__(self, *args):
	moose.Cell.__init__(self, *args)        
	comp = []
        self.num_comp = 59
	dendrites = set()
	level = defaultdict(set)
	self.presyn = 57
        comp.append(None) # First position is kept for matching index with FORTRAN       
	for ii in range(1, self.num_comp + 1):
	    comp.append(MyCompartment('comp_' + str(ii), self))
        # Assign levels to the compartments
	level[ 1].add( comp[ 1]) 
	level[ 2].add( comp[ 2]) 
	level[ 3].add( comp[ 3]) 
	level[ 3].add( comp[ 4]) 
	level[ 4].add( comp[ 5]) 
	level[ 4].add( comp[ 6]) 
	level[ 4].add( comp[ 7]) 
	level[ 5].add( comp[ 8]) 
	level[ 5].add( comp[ 9]) 
	level[ 5].add( comp[ 10])
	level[ 6].add( comp[ 11])
	level[ 7].add( comp[ 12])
	level[ 8].add( comp[ 13])
	level[ 9].add( comp[ 14])
	level[ 2].add( comp[ 15])
	level[ 3].add( comp[ 16])
	level[ 3].add( comp[ 17])
	level[ 4].add( comp[ 18])
	level[ 4].add( comp[ 19])
	level[ 4].add( comp[ 20])
	level[ 5].add( comp[ 21])
	level[ 5].add( comp[ 22])
	level[ 5].add( comp[ 23])
	level[ 6].add( comp[ 24])
	level[ 7].add( comp[ 25])
	level[ 8].add( comp[ 26])
	level[ 9].add( comp[ 27])
	level[ 2].add( comp[ 28])
	level[ 3].add( comp[ 29])
	level[ 3].add( comp[ 30])
	level[ 4].add( comp[ 31])
	level[ 4].add( comp[ 32])
	level[ 4].add( comp[ 33])
	level[ 5].add( comp[ 34])
	level[ 5].add( comp[ 35])
	level[ 5].add( comp[ 36])
	level[ 6].add( comp[ 37])
	level[ 7].add( comp[ 38])
	level[ 8].add( comp[ 39])
	level[ 9].add( comp[ 40])
	level[ 2].add( comp[ 41])
	level[ 3].add( comp[ 42])
	level[ 3].add( comp[ 43])
	level[ 4].add( comp[ 44])
	level[ 4].add( comp[ 45])
	level[ 4].add( comp[ 46])
	level[ 5].add( comp[ 47])
	level[ 5].add( comp[ 48])
	level[ 5].add( comp[ 49])
	level[ 6].add( comp[ 50])
	level[ 7].add( comp[ 51])
	level[ 8].add( comp[ 52])
	level[ 9].add( comp[ 53])
	level[ 0].add( comp[ 54])
	level[ 0].add( comp[ 55])
	level[ 0].add( comp[ 56])
	level[ 0].add( comp[ 57])
	level[ 0].add( comp[ 58])
	level[ 0].add( comp[ 59])

	for key, comp_set in level.items():
            if (key >= 2):
                dendrites |= comp_set
        
	self.level = level
	self.comp = comp
	self.dendrites = dendrites
	self.soma = comp[1]
        self.axon = [c for c in self.level[0]]

    # this is full of cycles - the traubConnect function is intended
    # to avoid the cycles
	comp[1].traubConnect(comp[ 54])
	comp[1].traubConnect(comp[ 2]) 
	comp[1].traubConnect(comp[ 15])
	comp[1].traubConnect(comp[ 28])
	comp[1].traubConnect(comp[ 41])
	comp[2].traubConnect(comp[ 3]) 
	comp[2].traubConnect(comp[ 4]) 
	comp[3].traubConnect(comp[ 4]) 
	comp[3].traubConnect(comp[ 5]) 
	comp[3].traubConnect(comp[ 6]) 
	comp[4].traubConnect(comp[ 7]) 
	comp[5].traubConnect(comp[ 6]) 
	comp[5].traubConnect(comp[ 8]) 
	comp[6].traubConnect(comp[ 9]) 
	comp[7].traubConnect(comp[ 10])
	comp[8].traubConnect(comp[ 11])
	comp[11].traubConnect(comp[12])
	comp[12].traubConnect(comp[13])
	comp[13].traubConnect(comp[14])
	comp[15].traubConnect(comp[16])
	comp[15].traubConnect(comp[17])
	comp[16].traubConnect(comp[17])
	comp[16].traubConnect(comp[18])
	comp[16].traubConnect(comp[19])
	comp[17].traubConnect(comp[20])
	comp[18].traubConnect(comp[19])
	comp[18].traubConnect(comp[21])
	comp[19].traubConnect(comp[22])
	comp[20].traubConnect(comp[23])
	comp[21].traubConnect(comp[24])
	comp[24].traubConnect(comp[25])
	comp[25].traubConnect(comp[26])
	comp[26].traubConnect(comp[27])
	comp[28].traubConnect(comp[29])
	comp[28].traubConnect(comp[30])
	comp[29].traubConnect(comp[30])
	comp[29].traubConnect(comp[31])
	comp[29].traubConnect(comp[32])
	comp[30].traubConnect(comp[33])
	comp[31].traubConnect(comp[32])
	comp[31].traubConnect(comp[34])
	comp[32].traubConnect(comp[35])
	comp[33].traubConnect(comp[36])
	comp[34].traubConnect(comp[37])
	comp[37].traubConnect(comp[38])
	comp[38].traubConnect(comp[39])
	comp[39].traubConnect(comp[40])
	comp[41].traubConnect(comp[42])
	comp[41].traubConnect(comp[43])
	comp[42].traubConnect(comp[43])
	comp[42].traubConnect(comp[44])
	comp[42].traubConnect(comp[45])
	comp[43].traubConnect(comp[46])
	comp[44].traubConnect(comp[45])
	comp[44].traubConnect(comp[47])
	comp[45].traubConnect(comp[48])
	comp[46].traubConnect(comp[49])
	comp[47].traubConnect(comp[50])
	comp[50].traubConnect(comp[51])
	comp[51].traubConnect(comp[52])
	comp[52].traubConnect(comp[53])
	comp[54].traubConnect(comp[55])
	comp[55].traubConnect(comp[56])
	comp[55].traubConnect(comp[58])
	comp[56].traubConnect(comp[57])
	comp[56].traubConnect(comp[58])
	comp[58].traubConnect(comp[59])

	comp[ 1].diameter = 2e-6 * 7.5 
	comp[ 2].diameter = 2e-6 * 1.06 
	comp[ 3].diameter = 2e-6 * 0.666666667 
	comp[ 4].diameter = 2e-6 * 0.666666667 
	comp[ 5].diameter = 2e-6 * 0.418972332 
	comp[ 6].diameter = 2e-6 * 0.418972332 
	comp[ 7].diameter = 2e-6 * 0.666666667 
	comp[ 8].diameter = 2e-6 * 0.418972332 
	comp[ 9].diameter = 2e-6 * 0.418972332 
	comp[ 10].diameter = 2e-6 * 0.666666667 
	comp[ 11].diameter = 2e-6 * 0.418972332 
	comp[ 12].diameter = 2e-6 * 0.418972332 
	comp[ 13].diameter = 2e-6 * 0.418972332 
	comp[ 14].diameter = 2e-6 * 0.418972332 
	comp[ 15].diameter = 2e-6 * 1.06 
	comp[ 16].diameter = 2e-6 * 0.666666667 
	comp[ 17].diameter = 2e-6 * 0.666666667 
	comp[ 18].diameter = 2e-6 * 0.418972332 
	comp[ 19].diameter = 2e-6 * 0.418972332 
	comp[ 20].diameter = 2e-6 * 0.666666667 
	comp[ 21].diameter = 2e-6 * 0.418972332 
	comp[ 22].diameter = 2e-6 * 0.418972332 
	comp[ 23].diameter = 2e-6 * 0.666666667 
	comp[ 24].diameter = 2e-6 * 0.418972332 
	comp[ 25].diameter = 2e-6 * 0.418972332 
	comp[ 26].diameter = 2e-6 * 0.418972332 
	comp[ 27].diameter = 2e-6 * 0.418972332 
	comp[ 28].diameter = 2e-6 * 1.06 
	comp[ 29].diameter = 2e-6 * 0.666666667 
	comp[ 30].diameter = 2e-6 * 0.666666667 
	comp[ 31].diameter = 2e-6 * 0.418972332 
	comp[ 32].diameter = 2e-6 * 0.418972332 
	comp[ 33].diameter = 2e-6 * 0.666666667 
	comp[ 34].diameter = 2e-6 * 0.418972332 
	comp[ 35].diameter = 2e-6 * 0.418972332 
	comp[ 36].diameter = 2e-6 * 0.666666667 
	comp[ 37].diameter = 2e-6 * 0.418972332 
	comp[ 38].diameter = 2e-6 * 0.418972332 
	comp[ 39].diameter = 2e-6 * 0.418972332 
	comp[ 40].diameter = 2e-6 * 0.418972332 
	comp[ 41].diameter = 2e-6 * 1.06 
	comp[ 42].diameter = 2e-6 * 0.666666667 
	comp[ 43].diameter = 2e-6 * 0.666666667 
	comp[ 44].diameter = 2e-6 * 0.418972332 
	comp[ 45].diameter = 2e-6 * 0.418972332 
	comp[ 46].diameter = 2e-6 * 0.666666667 
	comp[ 47].diameter = 2e-6 * 0.418972332 
	comp[ 48].diameter = 2e-6 * 0.418972332 
	comp[ 49].diameter = 2e-6 * 0.666666667 
	comp[ 50].diameter = 2e-6 * 0.418972332 
	comp[ 51].diameter = 2e-6 * 0.418972332 
	comp[ 52].diameter = 2e-6 * 0.418972332 
	comp[ 53].diameter = 2e-6 * 0.418972332 
	comp[ 54].diameter = 2e-6 * 0.7 
	comp[ 55].diameter = 2e-6 * 0.6 
	comp[ 56].diameter = 2e-6 * 0.5 
	comp[ 57].diameter = 2e-6 * 0.5 
	comp[ 58].diameter = 2e-6 * 0.5 
	comp[ 59].diameter = 2e-6 * 0.5 

        # Set the compartment length
	self.soma.length = 20e-6 
        for cc in self.dendrites:
            cc.length = 40e-6
        for cc in self.axon:
            cc.length = 50e-6

	

	
        t1 = datetime.now()
	    
	for ii, comp_set in level.items():
	    conductances = SpinyStellate.conductance[ii]
	    for compartment in comp_set:
                compartment.Em = SpinyStellate.Em
                compartment.initVm = SpinyStellate.Em
		for channel_name, density in conductances.items():
                    proto = self.channel_lib[channel_name]
       		    channel = moose.HHChannel(proto, channel_name, compartment)
                    if isinstance(proto, NaChannel):
                        channel.Ek = SpinyStellate.ENa
                    elif isinstance(proto, KChannel):
                        channel.Ek = SpinyStellate.EK
                    elif isinstance(proto, CaChannel):
                        channel.Ek = SpinyStellate.ECa
                    elif isinstance(proto, AR):
                        channel.Ek = SpinyStellate.EAR
                    else:
                        print 'ERROR: unknown channel type.'
                    if isinstance(proto, KC_FAST):
                        channel.Z = 0.0
                    else:
                        channel.X = 0.0
		    compartment.insertChannel(channel, specificGbar=density * 1e4) # convert density to SI
        spine_area_mult = 2.0
	for compartment in self.dendrites:
	    compartment.setSpecificRm(5.0 / spine_area_mult)
	    compartment.setSpecificRa(2.5)
	    compartment.setSpecificCm(spine_area_mult * 9e-3)
	    compartment.insertCaPool(5.2e-6 / 2e-10, 20e-3)
            for channel in compartment.channels:
                channel.Gbar *= spine_area_mult

	self.soma.setSpecificRm(5.0)
	self.soma.setSpecificRa(2.5)
        self.soma.setSpecificCm(9e-3)
        self.soma.insertCaPool(5.2e-6 / 2e-10, 50e-3)

	for compartment in self.axon:
	    compartment.setSpecificRm(0.1)
	    compartment.setSpecificRa(1.0)
            compartment.setSpecificCm(9e-3)

        t2 = datetime.now()
        delta = t2 - t1
        print 'insert channels: ', delta.seconds + 1e-6 * delta.microseconds


def has_cycle(comp):
    comp._visited = True
    ret = False
    for item in comp.raxial_list:
        if hasattr(item, '_visited') and item._visited:
            print 'Cycle between: ', comp.path, 'and', item.path
            return True
        ret = ret or has_cycle(item)
    return ret

def dump_cell(cell, filename):
    file_obj = open(filename, 'w')
    for lvl in cell.level:
        for comp in cell.level[lvl]:
            print comp.path
            file_obj.write(str(lvl) + ' ' + comp.get_props() + '\n')
    file_obj.close()

    
import pylab
from simulation import Simulation
import pymoose

if __name__ == '__main__':
    sim = Simulation()
    s = SpinyStellate('cell', sim.model)
    vm_table = s.comp[s.presyn].insertRecorder('Vm_ss', 'Vm', sim.data)
    
    pulsegen = s.soma.insertPulseGen('pulsegen', sim.model, firstLevel=3e-10, firstDelay=0.0, firstWidth=100e-3)
    ca_pool = moose.CaConc(s.soma.path + '/CaPool')
    ca_table = moose.Table('ca_conc', sim.data)
    ca_table.stepMode = 3
    ca_pool.connect('Ca', ca_table, 'inputRequest')
    for c in s.comp[1:]:
        if hasattr(c, 'ca_pool'):
            print '##?', c.name, c.ca_pool.B, c.ca_pool.tau
    sim.schedule()
    if has_cycle(s.soma):
        print "WARNING!! CYCLE PRESENT IN CICRUIT."
#     for chan in s.soma.channels:
#         print chan.name, 'Ek = ', chan.Ek, 'Gbar = ', chan.Gbar / s.soma.sarea()
    t1 = datetime.now()
    sim.run(100e-3)
    t2 = datetime.now()
    delta = t2 - t1
    print 'simulation time: ', delta.seconds + 1e-6 * delta.microseconds
    sim.dump_data('data')
    s.dump_cell('spinstell.txt')
    print 'soma:', 'Ra =', s.soma.Ra, 'Rm =', s.soma.Rm, 'Cm =', s.soma.Cm, 'Em =', s.soma.Em, 'initVm =', s.soma.initVm
    print 'dend:', 'Ra =', s.comp[2].Ra, 'Rm =', s.comp[2].Rm, 'Cm =', s.comp[2].Cm, 'Em =', s.comp[2].Em, 'initVm =', s.comp[2].initVm
#     for comp in s.comp:
#         for chan in comp.channels:
#             print chan.path, chan.Gbar/comp.sarea(), chan.Ek
    nrn_data = pylab.loadtxt('../nrn/mydata/Vm_ss.plot')
    nrn_vm = nrn_data[:, 1]
    nrn_t = nrn_data[:, 0]
    mus_vm = pylab.array(vm_table) * 1e3 # convert Neuron unit - mV
    mus_t = pylab.linspace(0, sim.simtime * 1e3, len(vm_table)) # convert simtime to neuron unit - ms
    pylab.plot(mus_t, mus_vm, 'r-', label='mus')
    pylab.plot(mus_t, ca_table, 'b-', label='ca')
    pylab.plot(nrn_t, nrn_vm, 'g-', label='nrn')
    pylab.legend()
    pylab.show()

# 
# brutespinstell.py ends here
