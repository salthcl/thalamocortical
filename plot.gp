set term x11 enh color;
set title 'NEURON vs MOOSE - AMPA Synapse';
set xlabel 'ms';


plot '/home/subha/src/sim/cortical/nrn/ampa.plot' u ($1):($2)  ti 'NEURON pre-Vm (mV)', \
     '/home/subha/src/sim/cortical/py/Va.dat' u ($0*1e-2):($1*1e3) w l  ti 'MOOSE pre-Vm (mV)', \
     '/home/subha/src/sim/cortical/nrn/ampa.plot' u ($1):($4*1e5) ti 'NEURON g-AMPA (uS)', \
     '/home/subha/src/sim/cortical/py/gAMPA.dat' u ($0*1e-2):($1*1e11) w l ti 'MOOSE g-AMPA (uS)', \
     '/home/subha/src/sim/cortical/nrn/ampa.plot' u ($1):($3)  ti 'NEURON post-Vm (mV)', \
     '/home/subha/src/sim/cortical/py/Vb.dat' u ($0*1e-2):($1*1e3) w l ti 'MOOSE post-Vm (mV)';
     

     
