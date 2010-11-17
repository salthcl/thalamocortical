#!/usr/bin/env python
# trbnetdata.py --- 
# 
# Filename: trbnetdata.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Thu Sep 16 16:19:39 2010 (+0530)
# Version: 
# Last-Updated: Wed Nov 17 14:31:59 2010 (+0530)
#           By: Subhasis Ray
#     Update #: 1111
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# igraph version of cell-cell graph generation for traub 2005 model
# 
# Initially the celltype graph was built from manually entered data in
# connmatrix.txt. Which contained an NxN matrix of all the cell
# types. The entry[i][j] had the number of presynaptic cells of
# celltype[i] connecting to each postsynaptic cell of celltype[j].  In
# addition, allowedcomp.py contained a dict ALLOWED_COMP which had a
# map between pairs of celltypes to a list of comprtment
# numbers. These are the compartment numbers in the second cell on
# which the first cell of the pair could form synapse.
#

# Change log:
#
# 2010-09-23 11:17:55 (+0530) -- now the celltype_graph has edges
# which have multiple attributes for all types of
# synapse. taugabafast, taugabaslow,
# 
# 2010-10-05 19:18:49 (+0530) -- changed _generate_celltype_graph and
# _generate_cell_graph to public methods generate_celltype_graph and
# generate_cell_graph. The idea is, I may want to manipulate the
# celltype-graph before generating the cell-graph - especially for
# scaling the synaptic conductances.
# 

# Code:

import sys
import os
from datetime import datetime
import numpy
import igraph as ig

import moose
import config
# synapse.py is imported for checking against the older version of the synaptic data.
import synapse
# allowedcomp is imported for verification with older data structure only
import allowedcomp



class TraubFullNetData(object):
    """Information about connectivity.

    This is hand coded datastructure for the Traub model network
    structure. In absense of the cell-type network graph or other
    files, this will be used as the master data.
    
    `celltype` -- list of celltypes
    
    `cellcount` -- list of cell-counts for each cell
                   type. cellcount[i] is the number of cells of type celltype[i]
                   present in the network.

    `pre_post_ratio` -- a square matrix represented by a list of lists
                        containing number of presynaptic cell of each
                        type connecting to each post-synaptic cell of
                        each type. pre_post_ratio[i][j] is the number
                        of cells of type celltype[i] forming synapse
                        on each cell of type celltype[j].

    """
    def __init__(self):
        self.celltype = ['SupPyrRS',
                         'SupPyrFRB',
                         'SupBasket',
                         'SupAxoaxonic',
                         'SupLTS',
                         'SpinyStellate',                          
                         'TuftedIB',
                         'TuftedRS',
                         'DeepBasket',
                         'DeepAxoaxonic',
                         'DeepLTS',
                         'NontuftedRS',
                         'TCR',
                         'nRT']

        self.cellcount = [1000,
                          50,
                          90,
                          90,
                          90,
                          240,
                          800,
                          200,
                          100,
                          100,
                          100,
                          500,
                          100,
                          100]

        
        self.pre_post_ratio = [[50,     50,     90,     90,     90,     3,      60,     60,     30,     30,     30,     3,      0,      0],
                               [5,      5,      5,	5,	5,	1,	3,	3,	3,	3,	3,	1,	0,	0],
                               [20,	20,	20,	20,	20,	20,	0,	0,	0,	0,	0,	0,	0,	0],
                               [20,	20,	0,	0,	0,	5,	5,	5,	0,	0,	0,	5,	0,	0],
                               [20,	20,	20,	20,	20,	20,	20,	20,	20,	20,	20,	20,	0,	0],
                               [20,	20,	20,	20,	20,	30,	20,	20,	20,	20,	20,	20,	0,	0],
                               [2,	2,	20,	20,	20,	20,	50,	20,	20,	20,	20,	20,	0,	0],
                               [2,	2,	20,	20,	20,	20,	20,	10,	20,	20,	20,	20,	0,	0],
                               [0,	0,	0,	0,	0,	20,	20,	20,	20,	20,	20,	20,	0,	0],
                               [5,	5,	0,	0,	0,	5,	5,	5,	0,	0,	0,	5,	0,	0],
                               [10,	10,	10,	10,	10,	20,	20,	20,	20,	20,	20,	20,	0,	0],
                               [10,	10,	10,	10,	10,	10,	10,	10,	10,	10,	10,	20,	20,	20],
                               [10,	10,	10,	10,	0,	0,	10,	10,	20,	10,	0,	10,	0,	25],
                               [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	15,	10]]

        self.tau_ampa = [[   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3,    0.0,    0.0],
                         [   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3,    0.0,    0.0],
                         [   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3,    0.0,    0.0],
                         [   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0],
                         [   2.0e-3,    2.0e-3,  0.8e-3,  0.8e-3, 1.0e-3, 2.0e-3, 2.0e-3, 2.0e-3,   0.8e-3,   0.8e-3,  1.0e-3,    2.0e-3, 2.0e-3, 2.0e-3],
                         [   2.0e-3,    2.0e-3,  1.0e-3,  1.0e-3,    0.0, 2.0e-3, 2.0e-3, 2.0e-3,   1.0e-3,   1.0e-3,     0.0,    2.0e-3,    0.0, 2.0e-3],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,    0.0]]

        # ta_nmda[suppyrrs][suppyrrs] = 130.0 ms according to paper, but 130.5 ms in code
        self.tau_nmda = [[ 130.5e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,   100e-3,    130e-3,    0.0,    0.0],
                         [ 130.0e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,   100e-3,    130e-3,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [   130e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,   100e-3,    130e-3,    0.0,    0.0],
                         [   130e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,   100e-3,    130e-3,    0.0,    0.0],
                         [   130e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,   100e-3,    130e-3,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0],
                         [   130e-3,    130e-3,  100e-3,  100e-3, 100e-3, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3, 100.0e-3,    130e-3, 130e-3, 100e-3],
                         [   130e-3,    130e-3,  100e-3,  100e-3,    0.0, 130e-3, 130e-3, 130e-3,   100e-3,   100e-3,      0.0,    130e-3,    0.0, 150e-3],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,      0.0,       0.0,    0.0,    0.0]]

        self.tau_gaba = [[      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [     6e-3,      6e-3,    3e-3,    3e-3,   3e-3,  6e-3,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [     6e-3,      6e-3,     0.0,     0.0,    0.0,  6e-3,   6e-3,   6e-3,      0.0,      0.0,     0.0,      6e-3,    0.0,  0.0 ],
                         [    20e-3,     20e-3,   20e-3,   20e-3,  20e-3, 20e-3,  20e-3,  20e-3,    20e-3,    20e-3,   20e-3,     20e-3,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,  6e-3,   6e-3,   6e-3,     3e-3,     3e-3,    3e-3,      6e-3,    0.0,  0.0 ],
                         [     6e-3,      6e-3,     0.0,     0.0,    0.0,  6e-3,   6e-3,   6e-3,      0.0,      0.0,     0.0,      6e-3,    0.0,  0.0 ],
                         [    20e-3,     20e-3,   20e-3,   20e-3,  20e-3, 20e-3,  20e-3,  20e-3,    20e-3,    20e-3,   20e-3,     20e-3,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,    0.0,  0.0 ],
                         [      0.0,       0.0,     0.0,     0.0,    0.0,   0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0, 3.3e-3, 9e-3 ]]

        # nRT_tau_gaba_slow - first entry nRT -> TCR, nRT->nRT
        self.nRT_TCR_tau_gaba_slow = 10e-3 
        self.nRT_nRT_tau_gaba_slow = 44.5e-3

        self.g_ampa_baseline = [
            [  0.25e-9,   0.25e-9,    3e-9,    3e-9,   2e-9, 0.1e-9, 0.1e-9, 0.1e-9,     1e-9,     1e-9,    1e-9,    0.5e-9,     0.0,     0.0 ],
            [  0.25e-9,   0.25e-9,    3e-9,    3e-9,   2e-9, 0.1e-9, 0.1e-9, 0.1e-9,     1e-9,     1e-9,    1e-9,    0.5e-9,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [     1e-9,      1e-9,    1e-9,    1e-9,   1e-9,   1e-9,   1e-9,   1e-9,     1e-9,     1e-9,    1e-9,      1e-9,     0.0,     0.0 ],
            [   0.5e-9,    0.5e-9,    1e-9,    1e-9,   1e-9, 0.5e-9,   2e-9,   2e-9,     3e-9,     3e-9,    2e-9,      2e-9,     0.0,     0.0 ],
            [   0.5e-9,    0.5e-9,    1e-9,    1e-9,   1e-9,  0.5-9,   1e-9,   1e-9,     3e-9,     3e-9,    2e-9,      1e-9,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ],
            [   0.5e-9,    0.5e-9,    1e-9,    1e-9,   1e-9, 0.5e-9,   1e-9,   1e-9,     3e-9,     3e-9,    2e-9,      1e-9, 0.75e-9,  0.5e-9 ],
            [   0.5e-9,    0.5e-9,  0.1e-9,  0.1e-9,    0.0,   1e-9, 1.5e-9, 1.5e-9,   1.5e-9,     1e-9,     0.0,      1e-9,     0.0, 0.75e-9 ],
            [      0.0,       0.0,     0.0,     0.0,    0.0,    0.0,    0.0,    0.0,      0.0,      0.0,     0.0,       0.0,     0.0,     0.0 ]]

        self.g_nmda_baseline = [
            [ 0.025e-9,  0.025e-9, 0.15e-9, 0.15e-9, 0.15e-9, 0.01e-9, 0.01e-9, 0.01e-9,   0.1e-9,   0.1e-9, 0.15e-9,   0.05e-9,      0.0,     0.0 ],
            [ 0.025e-9,  0.025e-9, 0.15e-9, 0.15e-9, 0.15e-9, 0.01e-9, 0.01e-9, 0.01e-9,   0.1e-9,   0.1e-9, 0.15e-9,   0.05e-9,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [   0.1e-9,    0.1e-9, 0.15e-9, 0.15e-9, 0.15e-9,  0.1e-9,  0.1e-9,  0.1e-9,  0.15e-9,  0.15e-9, 0.15e-9,    0.1e-9,      0.0,     0.0 ],
            [  0.05e-9,   0.05e-9, 0.15e-9, 0.15e-9, 0.15e-9, 0.05e-9,  0.2e-9,  0.2e-9,  0.15e-9,  0.15e-9, 0.15e-9,    0.2e-9,      0.0,     0.0 ],
            [  0.05e-9,   0.05e-9, 0.15e-9, 0.15e-9, 0.15e-9,  0.05-9,  0.1e-9,  0.1e-9,   0.1e-9,   0.1e-9,  0.1e-9,    0.1e-9,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ],
            [  0.05e-9,   0.05e-9,  0.1e-9,  0.1e-9,  0.1e-9, 0.05e-9,  0.1e-9,  0.1e-9,   0.1e-9,   0.1e-9,  0.1e-9,    0.1e-9, 0.075e-9, 0.05e-9 ],
            [  0.05e-9,   0.05e-9, 0.01e-9, 0.01e-9,     0.0,  0.1e-9, 0.15e-9, 0.15e-9,   0.1e-9,   0.1e-9,     0.0,    0.1e-9,      0.0, 0.15e-9 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0,      0.0,     0.0 ]]

        # for each nRT->TCR connections, g_gaba_baseline is taken from a uniform distribution in the range 0.7e-9 to 2.1e-9 Siemens.
        self.g_gaba_baseline = [
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [   1.2e-9,    1.2e-9,  0.2e-9,  0.2e-9,  0.5e-9,  0.1e-9,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [   1.2e-9,    1.2e-9,     0.0,     0.0,     0.0,  0.1e-9,    1e-9,    1e-9,      0.0,      0.0,     0.0,      1e-9, 0.0,    0.0 ],
            [  0.01e-9,   0.01e-9, 0.01e-9, 0.01e-9, 0.05e-9, 0.01e-9, 0.02e-9, 0.02e-9,  0.01e-9,  0.01e-9, 0.05e-9,   0.01e-9, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,  1.5e-9,  0.7e-9,  0.7e-9,   0.2e-9,   0.2e-9,  0.7e-9,    0.7e-9, 0.0,    0.0 ],
            [     1e-9,      1e-9,     0.0,     0.0,     0.0,  1.5e-9,    1e-9,    1e-9,      0.0,      0.0,     0.0,      1e-9, 0.0,    0.0 ],
            [  0.01e-9,   0.01e-9, 0.01e-9, 0.01e-9, 0.05e-9, 0.01e-9, 0.05e-9, 0.02e-9,  0.01e-9,  0.01e-9, 0.05e-9,   0.01e-9, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0,    0.0 ],
            [      0.0,       0.0,     0.0,     0.0,     0.0,     0.0,     0.0,     0.0,      0.0,      0.0,     0.0,       0.0, 0.0, 0.3e-9 ]]

        self.allowed_comps = [
            [# SupPyrRS
                [2,3,4,5,6,7,8,9,14,15,16,17,18,19,20,21,26, 27,28,29,30,31,32,33,10,11,12,13,22,23,24,25, 34,35,36,37], # SupPyrRS
                [2,3,4,5,6,7,8,9,14,15,16,17,18,19,20,21,26, 27,28,29,30,31,32,33,10,11,12,13,22,23,24,25, 34,35,36,37], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SpinyStellate
                [39,40,41,42,43,44,45,46], # TuftedIB
                [39,40,41,42,43,44,45,46], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # DeepLTS
                [38,39,40,41,42,43,44], # NontuftedRS
                [], # TCR 
                []], # nRT
            [ # SupPyrFRB
                [2,3,4,5,6,7,8,9,14,15,16,17,18,19,20,21,26, 27,28,29,30,31,32,33,10,11,12,13,22,23,24,25, 34,35,36,37], # SupPyrRS
                [2,3,4,5,6,7,8,9,14,15,16,17,18,19,20,21,26, 27,28,29,30,31,32,33,10,11,12,13,22,23,24,25, 34,35,36,37], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36, 44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SpinyStellate
                [39,40,41,42,43,44,45,46], # TuftedIB
                [39,40,41,42,43,44,45,46], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [38,39,40,41,42,43,44], # NontuftedRS
                [],
                []],
            [# SupBasket
                [1,2,3,4,5,6,7,8,9,38,39], # SupPyrRS
                [1,2,3,4,5,6,7,8,9,38,39], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupLTS
                [1,2,15,28,41], # SpinyStellate
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                []],
            [ # SupAxoaxonic
                [69],
                [69],
                [],
                [],
                [],
                [54],
                [56],
                [56],
                [],
                [],
                [],
                [45],
                [],
                []],
            [ # SupLTS
                [14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68] , # SupPyrRS
                [14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68], # SupPyrFRB
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # SupBasket
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # SupAxoaxonic
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # SupLTS
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # SpinyStellate
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55], # TuftedIB
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55], # TuftedRS
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # DeepBasket
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # DeepAxoaxonic
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # DeepLTS
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44], # NontuftedRS
                [],
                []],
            [ #SpinyStellate
                [ 2, 3, 4, 5, 6, 7, 8, 9,14,15,16,17,18,19,20,21,26,27,28,29,30,31,32,33], # SupPyrRS
                [ 2, 3, 4, 5, 6, 7, 8, 9,14,15,16,17,18,19,20,21,26,27,28,29,30,31,32,33], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SpinyStellate
                [7,8,9,10,11,12,36,37,38,39,40,41], # TuftedIB
                [7,8,9,10,11,12,36,37,38,39,40,41], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [37,38,39,40,41], # NontuftedRS
                [],
                []],
            [ #TuftedIB
                [40,41,42,43,44,45,46,47,48,49,50,51,52], #SupPyrRS
                [40,41,42,43,44,45,46,47,48,49,50,51,52], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SpinyStellate
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedIB
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44], # NontuftedRS
                [],
                []],
            [ # TuftedRS
                [40,41,42,43,44,45,46,47,48,49,50,51,52], # SupPyrRS
                [40,41,42,43,44,45,46,47,48,49,50,51,52], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SpinyStellate
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedIB
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44], # NontuftedRS
                [],
                []],
            [ # DeepBasket
                [],
                [],
                [],
                [],
                [],
                [1,2,15,28,41], # SpinyStellate
                [1,2,3,4,5,6,35,36], # TuftedIB
                [1,2,3,4,5,6,35,36], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [1,2,3,4,5,6,35,36], # NontuftedRS
                [],
                []],
            [ # DeepAxoaxonic
                [69],
                [69],
                [],
                [],
                [],
                [54],
                [56],
                [56],
                [],
                [],
                [],
                [45],
                [],
                []],
            [ # DeepLTS 
                [14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68], # SupPyrRS
                [14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68], # SupPyrFRB
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # SupBasket
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # SupAxoaxonic
                [8,9,10,11,12,21,22,23,24,25,34,35,36,37,38,47,48,49,50,51], # SupLTS
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # SpinyStellate
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55], # TuftedIB
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55], # TuftedRS
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # DeepBasket
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # DeepAxoaxonic
                [5,6,7,8,9,10,11,12,13,14,18,19,20,21,22,23,24,25,26,27,31,32,33,34,35,36,37,38,39,40,44,45,46,47,48,49,50,51,52,53], # DeepLTS
                [13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,38,39,40,41,42,43,44], #NontuftedRS
                [],
                []],
            [ # NontuftedRS
                [41,42,43,44], # SupPyrRS
                [41,42,43,44], # SupPyrFRB
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SupLTS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # SpinyStellate
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedIB
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47], # TuftedRS
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepBasket
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepAxoaxonic
                [5,6,7,8,9,10,18,19,20,21,22,23,31,32,33,34,35,36,44,45,46,47,48,49], # DeepLTS
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44],  # NontuftedRS
                [6,7,8,9,10,11,12,13,14,19,20,21,22,23,24,25,26,27,32,33,34,35,36,37,38,39,40,45,46,47,48,49,50,51,52,53,58,59,60,61,62,63,64,65,66,71,72,73,74,75,76,77,78,79,84,85,86,87,88,89,90,91,92,97,98,99,100,101,102,103,104,105,110,111,112,113,114,115,116,117,118,123,124,125,126,127,128,129,130,131], # TCR
                [2,3,4,15,16,17,28,29,30,41,42,43]], # nRT
            [ # TCR
                [45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68], # SupPyrRS
                [45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68], # SupPyrFRB
                [2,3,4,15,16,17,28,29,30,41,42,43], # SupBasket
                [2,3,4,15,16,17,28,29,30,41,42,43], # SupAxoaxonic
                [], # SupLTS
                [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53], # SpinyStellate
                [47,48,49,50,51,52,53,54,55], # TuftedIB
                [47,48,49,50,51,52,53,54,55], # TuftedRS
                [2,3,4,15,16,17,28,29,30,41,42,43], # DeepBasket
                [2,3,4,15,16,17,28,29,30,41,42,43], # DeepAxoaxonic
                [],
                [40,41,42,43,44], # NontuftedRS
                [],
                [2,3,4,15,16,17,28,29,30,41,42,43]], # nRT
            [ # nRT
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [1,2,15,28,41,54,67,80,93,106,119], # TCR
                [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53]] # nRT
            ]
        # ek_gaba depends only on the postsynaptic cell. ek_gaba[i] is for post synaptic cell of type celltype[i]
        self.ek_gaba = [-81e-3, -81e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -75e-3, -81e-3, -75e-3]
        # nRT->TCR GABAergic connections are taken from a unform random distribution between 0.7 nS and 2.1 nS.
        self.nRT_TCR_ggaba_high = 2.1e-9
        self.nRT_TCR_ggaba_low = 0.7e-9
        
    def check_pre_post_ratio(self):
        """Check the pre-post ratio for each celltype pair"""
        with open('connmatrix.txt') as connmatrix_file:
            index = -1
            for line in connmatrix_file.readlines():
                index += 1
                if index == 0:
                    print line
                    continue
                line = line.strip()
                if line == '':
                    continue
                values = line.split(',')
                # print values
                for ii in range(14):
                    if self.pre_post_ratio[index-1][ii] != int(values[ii]):
                        config.LOGGER.debug('pre-post ratio mismatch for %s-%s' % (self.celltype[index-1], self.celltype[ii]))
                        return False
        return True
                    
    def check_allowed_comps(self):
        """Compare the allowed_comps list to the original allowedcomp.py"""
        if len(self.allowed_comps) != 14:
            config.LOGGER.debug('Allowed_comp list must be of length 14. Got: %d' % (len(self.allowed_comps)))
            return False
        
        for index in range(len(self.allowed_comps)):
            if len(self.allowed_comps[index]) != 14:
                config.LOGGER.debug('Each row must lists for 14 cell types. But has %d for %s' % (len(self.allowed_comps[index]), self.celltype[index]))
                return False
        for ii in range(14):
            if self.celltype[ii].endswith('Axoaxonic'):
                continue
            for jj in range(14):
                try:
                    orig = allowedcomp.ALLOWED_COMP[self.celltype[ii]][self.celltype[jj]]
                    for kk in range(len(self.allowed_comps[ii][jj])):
                        if self.allowed_comps[ii][jj][kk] != orig[kk]:
                            config.LOGGER.debug('Valued don\'t match for %s -> %s' % (self.celltype[ii], self.celltype[jj]))
                            return False
                except KeyError:
                    if  self.allowed_comps[ii][jj] != []:
                        config.LOGGER.debug('Expected an empty list. But got something else for %s -> %s' % (self.celltype[ii], self.celltype[jj]))
                        return False
        return True


    def check_tau_ampa(self):
        """Compare the tau_AMPA with older version with dict."""        
        for pre_index in range(len(self.celltype)):
            for post_index in range(len(self.celltype)):
                left = self.tau_ampa[pre_index][post_index]
                try:
                    right = synapse.TAU_AMPA[self.celltype[pre_index]][self.celltype[post_index]]
                except KeyError:
                    if left!= 0.0:
                        config.LOGGER.debug('Key not present in synapse.py:TAU_AMPA - %s, %s' % (self.celltype[pre_index], self.celltype[post_index]))
                        return False
                    else:
                        right = 0.0
                if not numpy.allclose([left], [right]):
                    config.LOGGER.debug('Values not equal: TAU_AMPA - %s, %s: %g <> %g' % (self.celltype[pre_index], self.celltype[post_index], left, right))
                    return False
        return True

                        
    def check_tau_nmda(self):
        """Compare the tau_nmda with older version with dict."""        
        for pre_index in range(len(self.celltype)):
            for post_index in range(len(self.celltype)):
                left = self.tau_nmda[pre_index][post_index]
                try:
                    right = synapse.TAU_NMDA[self.celltype[pre_index]][self.celltype[post_index]]
                except KeyError:
                    if left != 0.0:
                        config.LOGGER.debug('Key not present in synapse.py:TAU_NMDA - %s, %s' % (self.celltype[pre_index], self.celltype[post_index]))
                        return False
                    else:
                        right = 0.0
                if not numpy.allclose([left], [right]):
                    config.LOGGER.debug('Values not equal: TAU_NMDA - %s, %s: %g <> %g' % (self.celltype[pre_index], self.celltype[post_index], left, right))
                    return False
        return True
                    
    def check_tau_gaba(self):
        """Compare the tau_gaba with older version with dict."""        
        for pre_index in range(len(self.celltype)):
            for post_index in range(len(self.celltype)):
                left = self.tau_gaba[pre_index][post_index]
                try:
                    if self.celltype[pre_index] == 'nRT':
                        right = synapse.TAU_GABA_FAST[self.celltype[pre_index]][self.celltype[post_index]]
                    else:
                        right = synapse.TAU_GABA[self.celltype[pre_index]][self.celltype[post_index]]
                except KeyError:
                    if left != 0.0:
                        config.LOGGER.debug('Key not present in synapse.py:TAU_GABA - %s, %s' % (self.celltype[pre_index], self.celltype[post_index]))
                        return False
                    else:
                        right = 0.0
                if not numpy.allclose([left], [right]):
                    config.LOGGER.debug('Values not equal: TAU_GABA - %s, %s: %g <> %g' % (self.celltype[pre_index], self.celltype[post_index], left, right))
                    return False
        return True
        
        


# 
# trbnetdata.py ends here
