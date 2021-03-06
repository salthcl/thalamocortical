# trbnet.py --- 
# 
# Filename: trbnet.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Mon Oct 11 17:52:29 2010 (+0530)
# Version: 
# Last-Updated: Mon Jul  1 20:45:50 2013 (+0530)
#           By: subha
#     Update #: 3310
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# This is for putting together the lessons learnt from experiments
# with Graph as data structure to represent the netwrok.
# 
# I note the following points: 
#
# 1. It is nice to have the defining data-structure as a graph.  Each
#    node represents a homogeneous population. The node attributes can
#    store population specific information.
#
#    The connectivity information can be stored in the edges. The edge
#    attributes represent the information on the synapses. Edge weight
#    can represent pre-post ratio (no. of presynaptic cell of type
#    source vertex connecting to each cell of type destination vertex).
#
# 2. For analyzing the simulation data, it will be useful to have
#    connectivity information for all relevant cells.
#
# 3. Decided to use HDF5 for data.  Need a clean way to associate
#    results of simulation with the model instance that was used. For
#    each cell's spike data, it should be possible to go back to the
#    model and see what was the connectivity for this cell. Thus model
#    is part of the data.
#
# 4. Testing: I tried to write some test code: but I realized midway
#    that this is rather circular. I am generating the graph using
#    manually entered data (TraubFullNetData). I am trying to validate
#    the celltype-graph against the celltype graph I generated
#    earlier. So if there is an error it will keep propagating. The only
#    reasonable test is manual check.
#
# 5. How to save the cell-graph?  After experimenting with
#    igraph/networkx and gml, graphml, pickle, formats, I tend towards
#    using simple adjacency matrices/edgelists with hdf5. Thus I can
#    have one single file for all the data (network info as well as
#    spikes).
#
#    More specifically, I'll save the final(post-scaling) g between
#    each pair of cells connected through a synapse.
#

# Change log:
#
# 2010-10-26 14:13:00 (+0530) finished implementation of methods
# _generate_celltype_graph and _read_celltype_graph
# 
# 2010-10-27 09:50:17 (+0530) implemented a simple test function to
# cross verify the celltype graph.
#
# 2010-11-09 17:44:03 (+0530) introduced pysparse module to utilize
# ll_mat for adjacency matrices for storing /g/.
# added creation of these matrices as part of generate_cell_graph fn.
# Updated scale_condunctance to take care of ggaba(nRT->TCR).
#
# 2010-12-28 14:26:47 (+0530) fixed serious mistake in
# get_maxdegree_cell_indices.
#
# 2011-09-08 11:10:12 (+0530) changed set_population to use
# ConfigParser object from config.py in stead of a custom cellcount
# file.
#
# Fri Jun 7 13:58:57 IST 2013 - realized some of the synaptic
# conductances were going negative when generated from normal
# distribution. Now I put code to set such entries to the mean value.
# 
# Mon Jul 1 10:40:47 IST 2013 - replace TCR cells with TimeTable
# objects. The TCR are just serving as spike generators, so no point
# doing the computationally expensive simulation of these cells. Add
# another config option for replacing these cells with TimeTable
# objects. The synaptic strengths should not be scaled.




# Code:
import sys
sys.path.append('/data/subha/chamcham_moose/python')
from collections import defaultdict
from datetime import datetime
import igraph
import h5py as h5
import numpy as np
import tables
import ConfigParser
from pysparse.sparse.spmatrix import ll_mat
import config
import moose
import pymoose
from trbnetdata import TraubFullNetData

# The cell classes
from compartment import MyCompartment
from cell import TraubCell
from spinystellate import SpinyStellate
from suppyrRS import SupPyrRS
from suppyrFRB import SupPyrFRB
from supbasket import SupBasket
from supaxoaxonic import SupAxoaxonic
from supLTS import SupLTS
from tuftedIB import TuftedIB
from deepbasket import DeepBasket
from deepaxoaxonic import DeepAxoaxonic
from deepLTS import DeepLTS
from tuftedRS import TuftedRS
from nontuftedRS import NontuftedRS
try:
    tcrtype = config.runconfig.get('stimulus', 'type').strip()
    config.LOGGER.debug('cell type for stimulus `%s, %s`' % (tcrtype, str(tcrtype == 'SpikeGen')))
    if tcrtype == 'SpikeGen':
        config.LOGGER.debug('###### here')
        from tcr_spikegen import TCR
        config.LOGGER.info('Imported TCR from tcr_spikegen')
    else:
        from tcr import TCR
        config.LOGGER.info('Imported TCR from tcr')
except KeyError:
    from tcr import TCR
    config.LOGGER.info('KeyError: Imported TCR from tcr')

from nRT import nRT
import synapse


layer_to_celltype = {
    '1': [],
    '2/3': ['SupPyrRS', 'SupPyrFRB', 'SupBasket', 'SupAxoaxonic', 'SupLTS'],
    '4': ['SpinyStellate'],
    '5': ['TuftedIB', 'TuftedRS'],
    '6': ['NontuftedRS', 'DeepBasket', 'DeepAxoaxonic', 'DeepLTS'],
    'Thalamus': ['nRT', 'TCR']
}

celltype_to_layer = {
    'SupPyrRS': ['2/3'],
    'SupPyrFRB': ['2/3'],
    'SupBasket': ['2/3'],
    'SupAxoaxonic': ['2/3'],
    'SupLTS': ['2/3'],
    'SpinyStellate': ['4'],
    'TuftedIB': ['5'],
    'TuftedRS': ['5'],
    'NonTuftedRS': ['6'],
    'DeepBasket': ['6'],
    'DeepAxoaxonic': ['6'],
    'DeepLTS': ['6'],
    'nRT': ['Thalamus'],
    'TCR': ['Thalamus']
}
# Is it a good idea to have a separate population class? What is the
# use?  When it comes to connectivity, the connectivity information is
# one level above the population. If a population is self contained,
# it should not know about other populations and thus not have
# connection probabilities dependent on the celltype of the other
# population.  If that connection information is not part of the
# population, it becomes just another container class. A set will do
# as well.

# class Population(object):
#     """Class to implement a homogeneous population"""

class CellType(tables.IsDescription):
    """The CellType class is data for each row in the celltype table.

    This is the datastructure used for saving celltype info hdf5 format.
    
    name -- human readable name of the celltype

    index -- index of the celltype in the table. Do we need explicit index??

    count -- number of cells of this celltype.

    """
    name = tables.StringCol(16)
    index = tables.Int8Col()
    count = tables.Int16Col()

class SynEdge(tables.IsDescription):
    """Describes an edge of celltype graph. This is used for saving
    synase information in HDF5 file."""
    # I think I should just subclass instead of keeping multiple alternate data entries
    source = tables.Int8Col()    # Index of source celltype
    target =  tables.Int8Col()   # Index of destination celltype
    weight =  tables.Float64Col() # connection probability from sourec to target
    gampa = tables.Float64Col()   # max conductance for source -> target AMPA synapse
    gnmda =  tables.Float64Col()  # max conductance for source -> target NMDA synapse
    tauampa = tables.Float64Col() # decay time constant for source -> target AMPA synapse
    taunmda =  tables.Float64Col() # decay time constant for source -> target NMDA synapse
    tau2nmda =  tables.Float64Col() # rise time constant for source -> target NMDA synapse (from NEURON mod file)
    taugaba =  tables.Float64Col()  # decay time constant for source -> target GABA synapse
    taugabaslow =  tables.Float64Col() # slower decay time constant for source -> target GABA synapse
    pscomps =  tables.UInt8Col(shape=(90, ))    # compartment nos in target cell where synapses are allowed
    ekgaba = tables.Float64Col() # reversal potential for gaba synapses
    ggaba =  tables.Float64Col(shape=(2)) # gaba conductance (distributed uniformly between first and second entry)
    prelease = tables.Float64Col() # Baseline synaptic release probability for this pair


def assign_comp_param_to_population(cells, compartment_no, field, values):
    assert(len(cells) == len(values))
    [setattr(cells[ii].comp[compartment_no], field, values[ii]) for ii in range(len(cells))]

class TraubNet(object):
    """Implements the full network in Traub et al 2005 model.

    celltype_file -- A file containing the celltype-celltype-graph.

    graph_format -- format of the celltype and other graphs to be read or saved.

    scale -- scale factor for all the populations.        

    populations -- a dictionary mapping each cell-class-name to a list
    of cells of that class.

    index_cell_map -- dictionary mapping a global index to a cell instance

    cell_index_map -- dictionary mapping a cell instance to a global index

    """
    def __init__(self, celltype_file=None, format=None, scale=None, container=None, netfile=None):
        """
        celltype_file -- A file containing the celltype-celltype-graph.

        format -- format of the celltype and other graphs to be read or saved.

        scale -- scale factor for all the populations.
        """
        self.from_netfile = None
        self.celltype_file = celltype_file
        self.scale = scale
        self.graph_format = format
        self.populations = defaultdict(list)
        self.celltype_graph = None
        self.cell_graph = None
        self.g_gaba_mat = None
        self.g_ampa_mat = None
        self.g_nmda_mat = None
        self.ps_comp_mat = None
        self.index_cell_map = {}
        self.cell_index_map = {}
        self.electrodes = []
        if not isinstance(container, moose.Neutral):
            if container is None:
                container = moose.Neutral('/')
            elif isinstance(container, str):
                container = moose.Neutral(container)
            else:
                raise Exception('Need a moose-object/string/None as container. Got %s of type %s' % (container, container.__class__.__name__))
            
        self.network_container = moose.Neutral('net', container)
        self.ectopic_container = moose.Neutral('ectopic_spikes', container)
        self.electrode_container = moose.Neutral('lfp', container)
        self.instrumentation = moose.Neutral('instru', container) # Container for various devices used in testing
        self.tweaks_doc = []
        if netfile is not None:
            self.read_network_model(netfile)
            self.from_netfile = netfile
            print 'Using netfile', netfile

    def setup_from_celltype_file(self, celltype_file=None, format=None, scale=None):
        """Set up the network from a celltype-celltype graph file.

        celltype_file -- the file containing the celltype-celltype-graph.

        format -- format of the celltype_file

        scale -- scale factor for the network
        """
        # if self.from_netfile is not None:
        #     config.LOGGER.info('Do nothing. Network loaded from %s' % (self.from_netfile))
        #     return

        if self.cell_graph is not None:
            del self.cell_graph
            self.cell_graph = None
        if celltype_file is not None:
            self.celltype_file = celltype_file
        if scale is not None:
            self.scale = scale
        elif self.scale is None:
            self.scale = 1.0
        if format is not None:
            self.format = format
        # self._generate_celltype_graph()
        self._read_celltype_graph()
                
    def setup(self):
        """Set up the master graph.
        """
        # if self.from_netfile is not None:
        #     config.LOGGER.info('Do nothing. Network loaded from %s' % (self.from_netfile))
        #     return
        if self.celltype_file is None:
            config.LOGGER.info('Setting up network from predefined structure with full network information.')
            self._generate_celltype_graph()
        else:
            self._read_celltype_graph()
        
    def _generate_celltype_graph(self):
        """Generate the celltype-graph as in Traub model (without the
        gapjunctions at this point).

        The generated graph will be manipulated to control the model
        to be instantiated.

        """
        tn = TraubFullNetData()
        self.celltype_graph = igraph.Graph(0, directed=True)
        self.celltype_graph.add_vertices(len(tn.celltype))
        self.nRT_TCR_ggaba_low = tn.nRT_TCR_ggaba_low
        self.nRT_TCR_ggaba_high = tn.nRT_TCR_ggaba_high
        self.frac_nRT_TCR_ggaba_fast = tn.frac_nRT_TCR_gaba_fast
        self.frac_nRT_nRT_ggaba_fast = tn.frac_nRT_nRT_gaba_fast
        edge_count = 0
        for celltype in self.celltype_graph.vs:
            celltype['label'] = tn.celltype[celltype.index]
            celltype['count'] = tn.cellcount[celltype.index]
            celltype['ectopicinterval'] = tn.ectopic_interval[celltype.index]
            for posttype in self.celltype_graph.vs:
                pre_post_ratio = tn.pre_post_ratio[celltype.index][posttype.index]
                if pre_post_ratio > 0:
                    self.celltype_graph.add_edges((celltype.index, posttype.index))
                    new_edge = self.celltype_graph.es[edge_count]
                    new_edge['weight'] = 1.0 * pre_post_ratio / celltype['count']
                    g_ampa_baseline = tn.g_ampa_baseline[celltype.index][posttype.index] 
                    new_edge['gampa'] = tn.g_ampa_baseline[celltype.index][posttype.index] * tn.tau_ampa[celltype.index][posttype.index]*1e3 / np.e # This is how gmax is related to c (baseline conductance scaling factor) for AMPA in traub model (e has unit of ms)
                    new_edge['gnmda'] = tn.g_nmda_baseline[celltype.index][posttype.index]
                    new_edge['tauampa'] = tn.tau_ampa[celltype.index][posttype.index]
                    new_edge['taunmda'] = tn.tau_nmda[celltype.index][posttype.index]
                    new_edge['taugaba'] = tn.tau_gaba[celltype.index][posttype.index]
                    new_edge['pscomps'] = str(tn.allowed_comps[celltype.index][posttype.index])
                    new_edge['ekgaba'] = tn.ek_gaba[posttype.index]
                    new_edge['ggaba'] = tn.g_gaba_baseline[celltype.index][posttype.index]
                    new_edge['prelease'] = tn.p_release[celltype.index][posttype.index]
                    if celltype['label'] == 'nRT':
                        if posttype['label'] == 'TCR':
                            new_edge['taugabaslow'] = tn.nRT_TCR_tau_gaba_slow
                            new_edge['ggaba'] = 'uniform %g %g' % (tn.nRT_TCR_ggaba_low, tn.nRT_TCR_ggaba_high) # How to specify distribution?
                        elif posttype['label'] == 'nRT':
                            new_edge['taugabaslow'] = tn.nRT_nRT_tau_gaba_slow                    
                    edge_count += 1
        for new_edge in self.celltype_graph.es:
            celltype = self.celltype_graph.vs[new_edge.source]
            posttype = self.celltype_graph.vs[new_edge.target]
            for key, value in new_edge.attributes().items():
                config.LOGGER.debug('## %s(%d)->%s(%d): %s = %s' % (celltype['label'], celltype.index, posttype['label'], posttype.index, key, str(value)))

    def _read_celltype_graph(self):
        """
        read the celltype graph from a graph file.
        """
        self.celltype_graph = igraph.read(self.celltype_file, format=self.graph_format)

    def _generate_cell_graph(self):
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Network loaded from %s' % (self.from_netfile))
            return
        print 'Netfile is empty'
        start = datetime.now()
        self.cell_graph = igraph.Graph(0, directed=True)
        total_count = 0
        for celltype in self.celltype_graph.vs:
            celltype['startindex'] = total_count
            cell_count = int(celltype['count'])
            config.LOGGER.debug('%s - population size %d' % (celltype['label'], cell_count))
            total_count += cell_count
        config.LOGGER.info('Total cell count: %d' % (total_count))
        self.g_gaba_mat = ll_mat(total_count, total_count)
        self.g_ampa_mat = ll_mat(total_count, total_count)
        self.g_nmda_mat = ll_mat(total_count, total_count)
        self.ps_comp_mat = ll_mat(total_count, total_count)
        syndistr = 'normal'
        try:
            syndistr = config.runconfig.get('synapse', 'distr')
        except KeyError:
            pass    
        config.LOGGER.info('using %s distribution for synaptic conductances' % (syndistr))
        for edge in self.celltype_graph.es:
            pre = edge.source
            post = edge.target
            pretype_vertex = self.celltype_graph.vs[pre]
            posttype_vertex = self.celltype_graph.vs[post]
            prestart = int(pretype_vertex['startindex'])
            poststart = int(posttype_vertex['startindex'])
            precount = int(pretype_vertex['count'])
            postcount = int(posttype_vertex['count'])
            connprob = float(edge['weight'])
            
            ps_comps = np.array(eval(edge['pscomps']), dtype=np.float)
            config.LOGGER.debug('Connecting populations: pre=%s[:%d], post=%s[:%d], probability=%g' % (pretype_vertex['label'], pretype_vertex['count'], posttype_vertex['label'], posttype_vertex['count'], connprob))
            config.LOGGER.debug('ggaba= %s, type:%s' % (str(edge['ggaba']), edge['ggaba'].__class__.__name__))
            config.LOGGER.debug('allowed postsynaptic compartments: %s (after conversion: %s)' % (edge['pscomps'], ps_comps))
            pre_per_post =  int(connprob * precount)
            # print 'Pre', pretype_vertex['label'], 'Post', posttype_vertex['label'], 'pre_per_post', pre_per_post, 'connprob', connprob, 'precount', precount
            if (connprob <= 0) or (len(ps_comps) == 0) or (precount <= 0) or (postcount <= 0) or (pre_per_post <= 0):
                continue
            # pre_indices[i] is the array of global indices of the
            # presynaptic cells connecting to the i-th postsynaptic
            # cell of posttype.
            pre_indices = np.random.randint(low=prestart, high=prestart+precount, size=(postcount,pre_per_post))
            # print 'Pre-indices', pre_indices
            # comp_indices[i][j] is the index of the postsynaptic
            # compartment in ps_comps for i-th postsynaptic
            # compartment for j-th presynaptic cell connecting to
            # postsynaptic cell
            comp_indices = np.random.randint(low=0, high=len(ps_comps), size=(postcount, pre_per_post))
            # syn_list is the list of global index pairs for synapses
            syn_list = np.array([[preindex, postindex + poststart]
                                    for postindex in range(postcount)
                                    for preindex in pre_indices[postindex]],
                                   dtype=np.int32)
            # print '========== START List of synapases ==========='
            # for item in syn_list:
            #     print item
            # print '========== END List of synapases ==========='
            config.LOGGER.debug(edge['pscomps'])
            indices = comp_indices.flatten()
            ps_comp_list = ps_comps[indices]
            config.LOGGER.debug('ps_comps list has length: %d, syn_list has length: %d' % (len(ps_comp_list), len(syn_list)))
            self.ps_comp_mat.put(ps_comp_list, syn_list[:,0], syn_list[:, 1])
            ampa_sd = float(config.runconfig.get('AMPA', 'sd'))
            g_ampa_mean = float(edge['gampa'])
            g_ampa = np.ones(len(syn_list)) * g_ampa_mean
            if pretype_vertex['label'] != 'TCR' and g_ampa_mean > 0 and ampa_sd > 0:
                ## Tue Mar 5 10:16:22 IST 2013 - Using lognormal in
                ## stead of normal distribution following Song et al
                ## (doi:10.1371/journal.pbio.0030068)
                ## Fri Jun  7 13:39:58 IST 2013 - discovered that normal distribution sample was going negative. - set them to mean

                if syndistr == 'normal':
                    g_ampa = np.random.normal(loc=g_ampa_mean, scale=ampa_sd*g_ampa_mean, size=len(syn_list))
                else:
                    norm_var = np.log(1 + (ampa_sd * ampa_sd)) # AMPA SD is specified as fraction of mean, hence v/m^2 becomes v = sd^2
                    norm_mean = np.log(g_ampa_mean) - norm_var * 0.5
                    g_ampa = np.random.lognormal(mean=norm_mean, sigma=np.sqrt(norm_var), size=len(syn_list))
                sample_g_ampa_mean = np.mean(g_ampa)
                sample_error = abs((sample_g_ampa_mean - g_ampa_mean) / g_ampa_mean)
                config.LOGGER.info('computed g_ampa_mean is %g and specified is %g' % (sample_g_ampa_mean, g_ampa_mean))
                if sample_error > 0.1:
                    config.LOGGER.warning('computed mean gampa has error > 10 percent: %g' % (sample_error*100))
                sample_g_ampa_std = np.std(g_ampa)
                config.LOGGER.info('computed g_ampa_sd is %g and specified is %g' % (sample_g_ampa_std/g_ampa_mean, ampa_sd))
                sample_error = abs((sample_g_ampa_std / g_ampa_mean - ampa_sd) / ampa_sd)
                if sample_error > 0.1:
                    config.LOGGER.warning('computed gampa std has error > 10 percent: %g' % (sample_error * 100))
            g_ampa[g_ampa < 0] = g_ampa_mean
            self.g_ampa_mat.put(g_ampa,
                                syn_list[:, 0], syn_list[:,1])
            
            ## Wed Mar 6 09:56:51 IST 2013 - Since the ratio of
            ## AMP/NMDA remains more or less constant between
            ## celltypes (Myme et al; doi: 10.1152/jn.00070.2003),
            ## scale NMDA conductance based on already generated AMPA
            ## conductance. Hence commented out below
            
            # nmda_sd should be set to 0 for lognorm
            # distribution. otherwise it is normally distributed to
            # replicate old settings.
            g_nmda_mean = float(edge['gnmda'])
            nmda_sd = float(config.runconfig.get('NMDA', 'sd'))
            g_nmda = np.ones(len(syn_list)) * g_nmda_mean
            if syndistr == 'normal' and g_nmda_mean > 0 and nmda_sd > 0:
                g_nmda = np.random.normal(loc=g_nmda, scale=nmda_sd*g_nmda_mean, size=len(syn_list))
            if syndistr == 'lognorm' and pretype_vertex['label'] != 'TCR' and g_ampa_mean > 0:
                g_nmda *= g_ampa / g_ampa_mean
            g_nmda[g_nmda < 0] = float(edge['gnmda'])
            self.g_nmda_mat.put(g_nmda,
                                syn_list[:, 0], syn_list[:,1])
            g_gaba = 0.0
            if (pretype_vertex['label'] == 'nRT') and (posttype_vertex['label'] == 'TCR'):
                g_gaba = np.random.uniform(self.nRT_TCR_ggaba_low,
                                           self.nRT_TCR_ggaba_high, 
                                           size=len(syn_list))
            else:
                gaba_sd = float(config.runconfig.get('GABA', 'sd'))
                g_gaba_mean = float(edge['ggaba'])
                g_gaba = g_gaba_mean
                if g_gaba_mean > 0 and gaba_sd > 0:
                    ## Tue Mar 5 10:16:22 IST 2013 - Using lognormal in
                    ## stead of normal distribution following Song et al
                    ## (doi:10.1371/journal.pbio.0030068)
                    if syndistr == 'normal':
                        g_gaba = np.random.normal(loc=g_gaba_mean, scale=gaba_sd*g_gaba_mean, size=len(syn_list))
                    elif syndistr == 'lognorm':
                        norm_var = np.log(1 + (gaba_sd * gaba_sd))
                        norm_mean = np.log(g_gaba_mean) - norm_var * 0.5
                        g_gaba = np.random.lognormal(mean=norm_mean, sigma=np.sqrt(norm_var), size=len(syn_list))
                    g_gaba[g_gaba < 0] = g_gaba_mean
                    sample_g_gaba_mean = np.mean(g_gaba)
                    sample_error = abs((sample_g_gaba_mean - g_gaba_mean) / g_gaba_mean)
                    config.LOGGER.info('computed g_gaba_mean is %g and specified is %g' % (sample_g_gaba_mean, g_gaba_mean))
                    if sample_error > 0.1:
                        config.LOGGER.warning('computed mean ggaba has error > 10 per cent: %g' % (sample_error*100))
                    sample_g_gaba_std = np.std(g_gaba)
                    config.LOGGER.info('computed g_gaba_sd is %g and specified is %g' % (sample_g_gaba_std/g_gaba_mean, gaba_sd))
                    sample_error = abs((sample_g_gaba_std / g_gaba_mean - gaba_sd) / gaba_sd)
                    if sample_error > 0.1:
                        config.LOGGER.warning('computed ggaba std has error > 10 percent: %g' % (sample_error * 100))
            self.g_gaba_mat.put(g_gaba,
                                syn_list[:,0],
                                syn_list[:,1])
        end = datetime.now()
        delta = end - start
        config.BENCHMARK_LOGGER.info('cell-cell network generation in: %g s' % (delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))

    def create_network(self):
        """Instantiate the network in MOOSE"""
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Network loaded from %s' % (self.from_netfile))
            return
        config.LOGGER.debug('Creating network')
        synchan_classname = 'SynChan'
        nmdachan_classname = 'NMDAChan'
        if config.stochastic:
            synchan_classname = 'STPSynChan'
            nmdachan_classname = 'STPNMDAChan'
            nmda_deltaF = float(config.runconfig.get('NMDA', 'deltaF'))
            nmda_d1 = float(config.runconfig.get('NMDA', 'd1'))
            nmda_d2 = float(config.runconfig.get('NMDA', 'd2'))
            nmda_tauD1 = float(config.runconfig.get('NMDA', 'tauD1'))
            nmda_tauD2 = float(config.runconfig.get('NMDA', 'tauD2'))
            nmda_tauF = float(config.runconfig.get('NMDA', 'tauF'))
            nmda_initPr = float(config.runconfig.get('NMDA', 'initPr'))
            ampa_deltaF = float(config.runconfig.get('AMPA', 'deltaF'))
            ampa_d1 = float(config.runconfig.get('AMPA', 'd1'))
            ampa_d2 = float(config.runconfig.get('AMPA', 'd2'))
            ampa_tauD1 = float(config.runconfig.get('AMPA', 'tauD1'))
            ampa_tauD2 = float(config.runconfig.get('AMPA', 'tauD2'))
            ampa_tauF = float(config.runconfig.get('AMPA', 'tauF'))
            ampa_initPr = float(config.runconfig.get('GABA', 'initPr'))
            gaba_deltaF = float(config.runconfig.get('GABA', 'deltaF'))
            gaba_d1 = float(config.runconfig.get('GABA', 'd1'))
            gaba_d2 = float(config.runconfig.get('GABA', 'd2'))
            gaba_tauD1 = float(config.runconfig.get('GABA', 'tauD1'))
            gaba_tauD2 = float(config.runconfig.get('GABA', 'tauD2'))
            gaba_tauF = float(config.runconfig.get('GABA', 'tauF'))
            gaba_initPr = float(config.runconfig.get('GABA', 'initPr'))

        starttime = datetime.now()
        total_count = 0
        for celltype in self.celltype_graph.vs:
            cell_count = int(celltype['count'])
            cell_class = eval(celltype['label'])
            for ii in range(cell_count):
                cell = cell_class(cell_class.prototype, '%s/%s_%d' % (self.network_container.path, celltype['label'], ii))
                self.index_cell_map[total_count + ii] = cell
                self.cell_index_map[cell] = total_count + ii
                self.populations[celltype['label']].append(total_count + ii)
            total_count += cell_count
        endtime = datetime.now()
        delta = endtime - starttime
        config.BENCHMARK_LOGGER.info('Time to create %d cells: %g s' % (total_count, delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))
        
        for syn_edge in self.celltype_graph.es:
            pretype_vertex = self.celltype_graph.vs[syn_edge.source]
            posttype_vertex = self.celltype_graph.vs[syn_edge.target]
            delay = synapse.SYNAPTIC_DELAY_DEFAULT
            p_release = syn_edge['prelease']
            if pretype_vertex['label'] in ['nRT', 'TCR']:            
                if posttype_vertex['label'] not in ['nRT', 'TCR']:
                    delay = synapse.SYNAPTIC_DELAY_THALAMOCORTICAL
            else:
                if posttype_vertex['label'] in ['nRT', 'TCR']:
                    delay = synapse.SYNAPTIC_DELAY_CORTICOTHALAMIC
            prestart = int(pretype_vertex['startindex'])
            poststart = int(posttype_vertex['startindex'])
            precount = int(pretype_vertex['count'])
            postcount = int(posttype_vertex['count'])
            # We loop through all pairs of pre and postsynaptic cell
            # index. postcompindex will be nonzero only for those
            # pairs having valid synapse.
            for pre_index in range(prestart, prestart+precount):
                precell = self.index_cell_map[pre_index]
                precomp = precell.comp[precell.presyn]
                for post_index in range(poststart, poststart+postcount):
                    postcell = self.index_cell_map[post_index]
                    # self.ps_comp_mat will be holding the compartment index for pre-post cell pair.
                    postcompindex = int(self.ps_comp_mat[pre_index, post_index])
                    if postcompindex > 255:
                        raise Exception('%s->%s -- PS comp has absurd index %d' % (precell.path, postcell.path, postcompindex))
                    if postcompindex > 0 and pre_index == post_index:
                        config.LOGGER.warning('Ignoring self connection: %s->%s (comp # %d)' % (precell.path, postcell.path, postcompindex))
                        continue
                    elif postcompindex == 0:
                        continue                                            
                    postcomp = postcell.comp[postcompindex]
                    if postcomp is None:
                        continue
                    g_ampa = self.g_ampa_mat[pre_index, post_index]
                    if g_ampa > 0.0:
                        synchan = precomp.makeSynapse(postcomp, 
                                            name='ampa_from_%s' % (pretype_vertex['label']), 
                                            classname=synchan_classname, 
                                            Ek=0.0, 
                                            Gbar=g_ampa, 
                                            tau1=syn_edge['tauampa'], 
                                            tau2=syn_edge['tauampa'], 
                                            Pr=p_release, 
                                            delay=delay)
                        if config.stochastic:
                            synchan.deltaF = ampa_deltaF
                            synchan.d1 = ampa_d1
                            synchan.d2 = ampa_d2
                            synchan.tauF = ampa_tauF
                            synchan.tauD1 = ampa_tauD1
                            synchan.tauD2 = ampa_tauD2
                            synchan.initPr[synchan.numSynapses-1] = ampa_initPr
                    g_nmda = self.g_nmda_mat[pre_index, post_index]
                    if g_nmda > 0.0:
                        # NMDA synapse model is weird in that we use
                        # the product of saturation and Gbar as an
                        # upper limit on the conductance. On the other
                        # hand, the actual synaptic weight is also set
                        # to what is considered as Gbar for SynChan.
                        synchan = precomp.makeSynapse(postcomp, 
                                                      name='nmda_from_%s' % (pretype_vertex['label']), 
                                                      classname=nmdachan_classname, 
                                                      Ek=0.0,
                                                      Gbar=g_nmda,
                                                      weight=g_nmda,
                                                      tau1=syn_edge['taunmda'], 
                                                      tau2=5e-3, 
                                                      Pr=p_release, 
                                                      delay=delay)
                        synchan.MgConc = TraubFullNetData.MgConc
                        synchan.saturation = 1.0                        
                        if config.stochastic:
                            synchan.deltaF = nmda_deltaF
                            synchan.d1 = nmda_d1
                            synchan.d2 = nmda_d2
                            synchan.tauF = nmda_tauF
                            synchan.tauD1 = nmda_tauD1
                            synchan.tauD2 = nmda_tauD2
                            synchan.initPr[synchan.numSynapses-1] = nmda_initPr
                    g_gaba = self.g_gaba_mat[pre_index, post_index]
                    if g_gaba > 0.0:
                        g_gaba_slow = 0.0
                        if syn_edge['taugabaslow'] > 0.0:
                            if pretype_vertex['label'] == 'nRT':
                                if posttype_vertex['label'] == 'nRT':                                
                                    g_gaba_slow = g_gaba * (1 - self.frac_nRT_nRT_ggaba_fast)
                                    g_gaba = g_gaba * self.frac_nRT_nRT_ggaba_fast
                                elif posttype_vertex['label'] == 'TCR':
                                    g_gaba_slow = g_gaba *  (1 - self.frac_nRT_TCR_ggaba_fast)
                                    g_gaba = g_gaba * self.frac_nRT_TCR_ggaba_fast
                                synchan = precomp.makeSynapse(postcomp, 
                                                    name='gaba_slow_from_%s' % (pretype_vertex['label']), 
                                                    classname=synchan_classname, 
                                                    Ek=syn_edge['ekgaba'], 
                                                    Gbar=g_gaba_slow, 
                                                    tau1=syn_edge['taugabaslow'], 
                                                    tau2=0.0, 
                                                    Pr=p_release, 
                                                    delay=delay)                               
                                if config.stochastic:
                                    synchan.deltaF = gaba_deltaF
                                    synchan.d1 = gaba_d1
                                    synchan.d2 = gaba_d2
                                    synchan.tauF = gaba_tauF
                                    synchan.tauD1 = gaba_tauD1
                                    synchan.tauD2 = gaba_tauD2
                                    synchan.initPr[synchan.numSynapses-1] = gaba_initPr

                        synchan = precomp.makeSynapse(postcomp, 
                                            name='gaba_from_%s' % (pretype_vertex['label']), 
                                            classname=synchan_classname, 
                                            Ek=syn_edge['ekgaba'], 
                                            Gbar=g_gaba,
                                            tau1=syn_edge['taugaba'], 
                                            tau2=0.0, 
                                            Pr=p_release, 
                                            delay=delay)
                        if config.stochastic:
                            synchan.deltaF = gaba_deltaF
                            synchan.d1 = gaba_d1
                            synchan.d2 = gaba_d2
                            synchan.tauF = gaba_tauF
                            synchan.tauD1 = gaba_tauD1
                            synchan.tauD2 = gaba_tauD2
                            synchan.initPr[synchan.numSynapses-1] = gaba_initPr
                    config.LOGGER.debug('Set connections: %s->%s (comp # %d): ampa = %g, nmda = %g, gaba = %g' % (precell.path, postcell.path, postcompindex, g_ampa, g_nmda,  g_gaba))
        endtime = datetime.now()
        delta = endtime - starttime
        config.BENCHMARK_LOGGER.info('Finished network creation in: %g s' % (delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))

    def setup_ectopic_input(self):
        config.LOGGER.debug('Setting up ectopic input')
        for celltype in self.celltype_graph.vs:
            for ii in self.populations[celltype['label']]:
                cell = self.index_cell_map[ii]
                randspike = moose.RandomSpike('ectopic_%s' % (cell.name), self.ectopic_container)
                randspike.rate = 1/celltype['ectopicinterval']
                randspike.minAmp = 0.4e-9
                randspike.maxAmp = 0.4e-9
                randspike.reset = 1
                randspike.resetValue = 0.0
                target = cell.comp[cell.presyn]
                if target.className == 'Compartment':
                    success = randspike.connect('outputSrc', target, 'injectMsg')
                    config.LOGGER.debug('Connected %s to %s: %s' % (randspike.path, cell.comp[cell.presyn].path, str(success)))

    def setup_current_injection_test(self, inject_values, first_delay, width, data_container):
        """Set up a test for each cell with a set of current injections."""
        pulsegen = moose.PulseGen('inject_test', self.instrumentation)
        pulsegen.setCount(len(inject_values))
        for index in range(len(inject_values)):
            pulsegen.setLevel(index, inject_values[index])
            pulsegen.setWidth(index, width)
            pulsegen.setDelay(index, width)
            print 'Current injection:', index, pulsegen.getLevel(index), pulsegen.getDelay(index), pulsegen.getWidth(index)
        if first_delay > 0.0:
            pulsegen.firstDelay = first_delay
        for cell in self.cell_index_map.keys():
            pulsegen.connect('outputSrc', cell.soma, 'injectMsg')
        pulse_table = moose.Table('inject_test', data_container)
        pulse_table.stepMode = 3
        pulse_table.connect('inputRequest', pulsegen, 'output')

    def setup_lfp_recording(self, name, depth, data_container, cellclasses=[]):
        """Setup electrodes for recording LFP."""
        electrode = moose.Efield(name, self.electrode_container)
        self.electrodes.append(electrode)
        electrode.x = 0.0
        electrode.y = 0.0
        electrode.z = depth
        if cellclasses == []:
            for celltype in self.celltype_graph.vs:
                cellclasses.append(celltype['label'])

        for celltype in cellclasses:
            cellclass = eval(celltype)
            # nRT and TCR cells will be ignored
            if not hasattr(cellclass, 'depth') or cellclass.depth is  None:
                continue
            # first collect the indices of all the compartments that affect lfp
            comp_indices = []
            for level_no in cellclass.depth.keys():
                # print
                # print level_no, '-->',
                for comp_no in cellclass.level[level_no]:
                    # print comp_no, ',',
                    comp_indices.append(comp_no)
            # then connect all such compartments in all cells of this type to the electrode object.
            for ii in self.populations[celltype]:
                cell = self.index_cell_map[ii]
                # print 'cell:', cell.path, 'comps:', comp_indices
                for jj in comp_indices:
                    comp = cell.comp[jj]
                    result = comp.connect('ImSrc', electrode, 'currentDest')
                    if not result:
                        raise Exception('Failed to connect %s->%s' % (comp.path, electrode.path))
                    # else:
                    #     config.LOGGER.debug('Connected %s %s [pos=(%g, %g, %g)] to %s %s: %s' % (comp.className, comp.path, comp.x, comp.y, comp.z, electrode.className, electrode.path, str(result)))

        lfp_container = moose.Neutral('lfp', data_container)
        lfp_table = moose.Table(name, lfp_container)
        lfp_table.stepMode = 3
        electrode.connect('potential', lfp_table, 'inputRequest')
        config.LOGGER.debug('Created electrode: %s at depth %g m' % (name, depth))
                               

    def get_maxdegree_cell_indices(self, celltype=None, size=None):
        """Get the cells with maximum connectivity - disregarding the strength of the synapse.

        returns the {size} cells of type {celltype} sorted by degree.
        
        """
        cell_dict = defaultdict(int)
        if celltype is not None:
            index = 0
            for vertex in self.celltype_graph.vs:
                if vertex['label'] == celltype:
                    for ii in range(index, index + vertex['count']):
                        for jj in range(self.g_gaba_mat.shape[1]):
                            if self.g_gaba_mat[ii, jj] != 0.0:
                                cell_dict[ii] += 1
                            if self.g_ampa_mat[ii, jj] != 0.0:
                                cell_dict[ii] += 1
                            if self.g_nmda_mat[ii, jj] != 0.0:
                                cell_dict[ii] += 1
                    break
                else:
                    index += vertex['count']
        else:
            for ii in range(self.g_gaba_mat.shape[0]):
                for jj in range(self.g_gaba_mat.shape[1]):
                    if self.g_gaba_mat[ii, jj] != 0.0:
                        cell_dict[ii] += 1
                    if self.g_ampa_mat[ii, jj] != 0.0:
                        cell_dict[ii] += 1
                    if self.g_nmda_mat[ii, jj] != 0.0:
                        cell_dict[ii] += 1
        cells = sorted(cell_dict, key=lambda x: cell_dict[x], reverse=True)
        if size is None:
            return cells
        else:
            return cells[:size]
            
    def setup_spike_recording(self, data_container):
        """Create tables to record spike times for each cell.

        The tables are created under {data_container}/spikes"""
        spike_container = moose.Neutral('spikes', data_container)
        # Is it correct to record the spikes from soma or the SpikeGen ?
        # 2012-07-14 12:28:38 (+0530) Switching to recording from presynaptic compartment.
        for cell in self.cell_index_map.keys():            
            comp = cell.comp[cell.presyn]                
            tab = comp.insertRecorder(cell.name, 'Vm', spike_container)
            config.LOGGER.info('Recording spike from: %s' % (comp.path))
            if not isinstance(comp, moose.TimeTable) and not isinstance(comp, moose.SpikeGen):
                tab.stepMode = moose.TAB_SPIKE
                tab.stepSize = -20e-3
        ectopic_container = moose.Neutral('%s/ectopic_spikes' % (data_container.path))
        for ch in self.ectopic_container.children():
            spike = moose.Neutral(ch)
            tab = moose.Table(spike.name, ectopic_container)
            tab.stepMode = moose.TAB_SPIKE
            tab.stepSize = 0.2e-9
            spike.connect('state', tab, 'inputRequest')
        
    def setup_Vm_recording(self, data_container, celltype, numcells=10, random=True):
        """Create tables to record Vm and [Ca2+] from a fixed number of cells of each type.

        The tables recording Vm are created under {data_container}/Vm and
        those for recording [Ca2+] are created under {data_container}/Ca.

        celltype -- the class of cells to record from.
        
        numcells -- number of cells to record from. If 'all', select all cells.

        random -- if true, randomly select {numcells} cells. if false, select only the maxdegree cells.    
        
        """
        vm_container = moose.Neutral('Vm', data_container)
        ca_container = moose.Neutral('Ca', data_container)
        syn_gk_container = moose.Neutral('synapse', data_container)
        if celltype == 'all':
            vs = self.celltype_graph.vs
        else:
            vs = self.celltype_graph.vs.select(label_eq=celltype)
        for vertex in vs:
            if not random:
                cell_list = self.get_maxdegree_cell_indices(celltype=vertex['label'], size=numcellspertype)
            else:
                pop = np.array(self.populations[celltype])
                high = len(pop)
                if high > numcells:
                    indices = np.random.randint(low=0, high=high, size=numcells)
                    cell_list = pop[indices]
                else:
                    cell_list = pop
            for cellindex in cell_list:
                cell = self.index_cell_map[cellindex]
                # Skip timetables replacing TCR cells
                if not isinstance(cell.comp[cell.presyn], moose.Compartment):
                    config.LOGGER.info('Skipping %s as it does not have Compartment for presyn.' % (cell.path))
                    continue
                cell.soma.insertRecorder(cell.name, 'Vm', vm_container)
                cell.soma.insertCaRecorder(cell.name, ca_container)
                if config.runconfig.get('record', 'gk_syn') not in ['YES', 'Yes', 'yes', '1', 'TRUE', 'True', 'true']:
                    continue
                synchan = moose.context.getWildcardList(cell.path + '/##[ISA=SynChan]', True)
                nmda = moose.context.getWildcardList(cell.path + '/##[TYPE=NMDAChan]', True)
                config.LOGGER.info('synchan: %s' % ([ch.path() for ch in synchan]))
                config.LOGGER.info('nmda: %s' % ([ch.path() for ch in nmda]))
                synlist = synchan + nmda
                for chan in synlist:
                    syn = moose.Neutral(chan)
                    comp = moose.Neutral(syn.parent)
                    tab = moose.Table('gk_%s_%s_%s' % (cell.name, comp.name, syn.name), syn_gk_container)
                    tab.stepMode = 3
                    success = tab.connect('inputRequest', syn, 'Gk')
                    config.LOGGER.info('Connected recording table: %s to %s: %s' % (tab.name, syn.name, success))
                    tab = moose.Table('Ik_%s_%s_%s' % (cell.name, comp.name, syn.name), syn_gk_container)
                    tab.stepMode = 3
                    success = tab.connect('inputRequest', syn, 'Ik')
                    config.LOGGER.info('Connected recording table: %s to %s: %s' % (tab.name, syn.name, success))


        
    def setup_stimulus(self, bg_cells='any', 
                       probe_cells='any',
                       stim_onset=1.0, 
                       bg_interval=0.5, 
                       bg_interval_spread=0.0,
                       num_bg_pulses=0,
                       pulse_width=60e-6, 
                       isi=10e-3, 
                       level=5e-12, 
                       bg_count=100, 
                       probe_count=10, 
                       stim_container='/stim',
                       data_container='/data'):
        """Setup the stimulus protocol.

        The protocol is as follows:

     ->|  |<- stim_onset
           __________________________________ gate
        __|
        ->|    |<- bg_interval

        _______||____||____||____||____||____  background
        
        _____________||__________||__________  probe


        Let the system stabilize for stim_onset seconds.

        Then turn the stim_gate on: which gates the triggers.

        The bg_trigger will trigger the background pulse
        generator. probe_trigger will trigger the probe pulse
        generator.

        bg_cells -- type of cells we are using as background or an
        explicit list of cells
        
        probe_cells -- type of cells we are looking at, or an explicit
        list of cells

        Ideally, background and probe cells should not overlap

        stim_onset -- when we consider the system stabilized and start
        stimulus

        bg_interval -- interval between two background stimulus
        sessions. probe stimulus will be applied at half the rate.

        bg_interval_spread -- upper limit for background interval for
        randomization. If 0, background pulse is at regular
        interval. Otherwise, it is uniformly distributed between
        bg_interval and bg_interval + bg_interval_spread.

        num_bg_pulses -- in case of randomized stimulus, this
        determines how many total background pulses to deliver.

        pulse_width -- width of background pulses

        isi -- if paired pulse, then the interval between the two
        pulses (beginning of second - beginning of first), 0 for
        single pulse.

        level -- current injection value.

        bg_count -- number of cells stimulated by background pulse.

        probe_count -- number of cells to be probed.

        stim_container -- container object for stimulating-electrodes

        2012-07-02 12:36:53 (+0530) Subhasis Ray
        
        Updating stimulus protocol to give trains (similar config
        change in custom.ini) The paired pulse does not work.

        2012-08-25 14:20:22 (+0530) Subhasis Ray

        Updating stimulus protocol to ramdomize pulses.

        """
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Using network file.')
            return
        config.LOGGER.debug('Setting up stimulus protocol: bg_interval: %g, pulse_width: %g, isi: %g' % (bg_interval, pulse_width, isi))
        self.create_stimulus_objects(stim_container, data_container)
        self.stim_gate.firstDelay = stim_onset
        delays = {}
        levels = {}
        widths = {}
        if bg_interval_spread > 0.0 and num_bg_pulses > 0:
            delay_list = np.random.uniform(low=bg_interval, high=bg_interval_spread+bg_interval, size=num_bg_pulses)
            print 'Delays:', delay_list
            for ii in range(len(delay_list)):
                delays[ii] = delay_list[ii]
                levels[ii] = level
                widths[ii] = pulse_width
        else:
            for key, value in config.runconfig.items('stimulus'):
                if key.startswith('delay_'):
                    index = int(key.rpartition('_')[-1])
                    delays[index] = float(value)
                elif key.startswith('level_'):
                    index = int(key.rpartition('_')[-1])
                    levels[index] = float(value)
                elif key.startswith('width_'):
                    index = int(key.rpartition('_')[-1])
                    widths[index] = float(value)
        # More than 1 delay values indicate we want to explicitly set
        # each pulse time and duration, with probe pulses with every
        # alternet background pulse.
        print delays, len(delays)
        if len(delays) > 1:
            self.stim_bg.count = len(delays)
            self.stim_probe.count = len(delays)/2+1
            for index in range(len(delays)):
                self.stim_bg.delay[index] = delays[index]
                print 'index:', index, 'delay:', self.stim_bg.delay[index]
                self.stim_bg.level[index] = levels[index]
                self.stim_bg.width[index] = widths[index]                    
                if (index % 2 == 0) and ((index + 1) < len(delays)):
                    self.stim_probe.delay[index/2] = delays[index] + delays[index+1]
                    self.stim_probe.level[index/2] = levels[index]
                    self.stim_probe.width[index/2] = widths[index]                    
        # A single delay value means we have an even pulse train
        else:
            self.stim_bg.firstLevel = level
            self.stim_bg.secondLevel = level
            self.stim_bg.firstDelay = bg_interval
            self.stim_bg.firstWidth = pulse_width
            self.stim_bg.secondDelay = isi
            self.stim_bg.secondWidth = pulse_width        
            self.stim_bg.trigMode = moose.EXT_GATE

            self.stim_probe.firstLevel = level
            self.stim_probe.secondLevel = level
            self.stim_probe.firstDelay = 2 * self.stim_bg.firstDelay + self.stim_bg.secondDelay + pulse_width
            self.stim_probe.secondDelay = isi
            self.stim_probe.firstWidth = pulse_width
            self.stim_probe.secondWidth = pulse_width            
            self.stim_probe.trigMode = moose.EXT_GATE
        # 2012-08-25 14:18:21 (+0530): Commenting out the following
        # line because we do not want to start probe after all
        # background pulses in one set are delivered, but with every
        # alternet pulse, which is achieved above.

        # self.stim_probe.delay[0] = self.stim_bg.delay[0]  + sum([self.stim_bg.delay[ii] for ii in range(self.stim_bg.count)]) + self.stim_bg.width[self.stim_bg.count - 1]
        
        

        config.LOGGER.debug('Background stimulus: firstDelay: %g, firstWidth: %g, firstLevel: %g, secondDelay: %g, secondWidth: %g, secondLevel: %g' % (self.stim_bg.firstDelay, self.stim_bg.firstWidth, self.stim_bg.firstLevel, self.stim_bg.secondDelay, self.stim_bg.secondWidth, self.stim_bg.secondLevel))
        config.LOGGER.debug('Probe stimulus: firstDelay: %g, firstWidth: %g, firstLevel: %g, secondDelay: %g, secondWidth: %g, secondLevel: %g' % (self.stim_probe.firstDelay, self.stim_probe.firstWidth, self.stim_probe.firstLevel, self.stim_probe.secondDelay, self.stim_probe.secondWidth, self.stim_probe.secondLevel))
        
        bg_cell_indices = []
        probe_cell_indices = []
        if isinstance(bg_cells, str) and isinstance(probe_cells, str) and bg_cells == probe_cells:
            cell_indices = []
            if bg_cells == 'any':
                cell_indices = np.arange(len(self.index_cell_map.keys()))
            else:
                celltype_vertex_set = self.celltype_graph.vs.select(label_eq=bg_cells)
                for vertex in celltype_vertex_set:
                    startindex = int(vertex['startindex'])
                    count = int(vertex['count'])
                    cell_indices = np.concatenate((cell_indices, np.arange(startindex, startindex+count)))
            np.random.shuffle(cell_indices)
            bg_cell_indices = cell_indices[:bg_count]
            probe_cell_indices = cell_indices[bg_count: bg_count+probe_count]
        else:            
            if isinstance(bg_cells, str):
                if bg_cells == 'any':
                    bg_cell_indices = np.arange(len(self.index_cell_map.keys()))
                    np.random.shuffle(bg_cell_indices)
                    bg_cell_indices = bg_cell_indices[:bg_count]
                else:
                    celltype_vertex_set = self.celltype_graph.vs.select(label_eq=bg_cells)
                    for vertex in celltype_vertex_set: # This  should loop only once
                        startindex = int(vertex['startindex'])
                        count = int(vertex['count'])
                        # print vertex['label'], startindex, count
                        cell_indices = np.arange(startindex, startindex+count)
                        np.random.shuffle(cell_indices)
                        # print indices
                        bg_cell_indices = np.concatenate((bg_cell_indices, cell_indices[:bg_count]))

            if isinstance(probe_cells, str):
                if probe_cells == 'any':
                    probe_cell_indices = np.arange(0, len(self.index_cell_map.keys()))
                    np.random.shuffle(probe_cell_indices)
                    probe_cell_indices = probe_cell_indices[:probe_count]
                else:
                    celltype_vertex_set = self.celltype_graph.vs.select(label_eq=probe_cells)
                    for vertex in celltype_vertex_set: # This should loop only once
                        startindex = int(vertex['startindex'])
                        count = int(vertex['count'])
                        # print vertex['label'], startindex, count
                        cell_indices = np.arange(startindex, startindex+count)
                        np.random.shuffle(cell_indices)
                        # print indices
                        probe_cell_indices = np.concatenate((probe_cell_indices, cell_indices[:probe_count]))
        bg_cell_list = []
        if isinstance(bg_cells, list):
            bg_cell_list = bg_cells
        else:
            for index in bg_cell_indices:
                bg_cell_list.append(self.index_cell_map[index])
        
        probe_cell_list = []
        if isinstance(probe_cells, list):
            probe_cell_list = probe_cells
        else:
            for index in probe_cell_indices:
                probe_cell_list.append(self.index_cell_map[index])
        bg_targets = []
        probe_targets = []
        for cell in bg_cell_list:
            if isinstance(cell, str):
                comp = moose.Compartment('%s/%s/comp_1' % (self.network_container.path, cell))
            elif isinstance(cell, moose.Cell): # Changing TraubCell to moose.Cell as it will include tcr_spikegen.TCR
                comp = cell.soma
            else:
                raise Exception('Unknown type object for bg target: %s' % (cell))
            if comp.className == 'Compartment':
                self.stim_bg.connect('outputSrc', comp, 'injectMsg')
            elif comp.className == 'SpikeGen':
                self.stim_bg.connect('outputSrc', comp, 'Vm')
                config.LOGGER.debug('connected %s to %s' % (self.stim_bg.path, comp.path))
                comp.threshold = level/2.0                
            bg_targets.append(comp.path)
        for cell in probe_cell_list:
            # print 'probe:', cell
            if isinstance(cell, str):
                comp = moose.Compartment('%s/%s/comp_1' % (self.network_container.path, cell))
            elif isinstance(cell, moose.Cell):
                comp = cell.soma
            else:
                raise Exception('Unknown type object for probe target: %s' % (cell))
            if comp.className == 'Compartment':
                self.stim_probe.connect('outputSrc', comp, 'injectMsg')
            elif comp.className == 'SpikeGen':
                self.stim_probe.connect('outputSrc', comp, 'Vm')
                config.LOGGER.debug('connected %s to %s' % (self.stim_probe.path, comp.path))
                comp.threshold = level/2.0   
                config.LOGGER.debug('%s: threshold=%g' % (comp.path, comp.threshold))
            probe_targets.append(comp.path)
        ret = { 'stim_onset': stim_onset,
                'bg_interval': bg_interval,
                'isi': isi,
                'pulse_width': pulse_width,
                'level': level,
                'bg_targets': bg_targets,
                'probe_targets': probe_targets }
        self.save_stim_protocol(ret)
        return ret
                
    def save_stim_protocol(self,
                           params):
        config.LOGGER.debug('Writing stimulus protocol file')
        with open('%s/protocol_%s' % (config.data_dir, config.filename_suffix), 'w') as protocol_file:
            protocol_file.write('onset: %g\nbg_interval: %g\nisi: %g\nwidth: %g\nlevel: %g\n' % (params['stim_onset'], params['bg_interval'], params['isi'], params['pulse_width'], params['level']))
            protocol_file.write('background_cells:\n')
            # print 'Printing background_cells and probe_cells'
            for path in params['bg_targets']:
                protocol_file.write('%s\n' % (path))
            protocol_file.write('probe_cells:\n')
            for path in params['probe_targets']:
                protocol_file.write('%s\n' % (path))
        

    def scale_populations(self, scale):
        """Scale the number of cells in each population by a factor."""
        raise NotImplementedError('This has been removed and not up to date')
        if self.cell_graph is not None:
            raise Warning('Cell-graph already instantiated. Cannot rescale.')
        for vertex in self.celltype_graph.vs:
            vertex['count'] *= scale
            
    
    def scale_conductance(self, conductance_name, scale_dict):
        """Scale a particular synaptic conductance between pairs of celltypes.

        conductance_name -- key for the conductance to be scaled, e.g., 'ggaba'

        scale_dict -- a dict mapping celltype-pairs (pre, post) to scale factor. example:
                      {('SupPyrRS', 'SpinyStellate'): 0.5,
                       ('SupPyrFRB', 'SupLTS'): 1.5}
                       If either member of the tuple is '*', all celltypes are assumed.
        """
        for celltype_pair, scale_factor in scale_dict.items():
            if not isinstance(celltype_pair, tuple): 
                raise Warning('The keys in the scale_dict must be tuples of celltypes. Got %s of type %s instead' % (str(celltype_pair), type(celltype_pair)))
            if celltype_pair[0] == '*':
                pretype_vertex_seq = self.celltype_graph.vs
            else:
                pretype_vertex_seq = self.celltype_graph.vs.select(label_eq=celltype_pair[0])
            if celltype_pair[1] == '*':
                posttype_vertex_seq = self.celltype_graph.vs
            else:
                posttype_vertex_seq = self.celltype_graph.vs.select(label_eq=celltype_pair[1])
            for pretype_vertex in pretype_vertex_seq:
                for posttype_vertex in posttype_vertex_seq:
                    try:
                        edge_id = self.celltype_graph.get_eid(pretype_vertex.index, posttype_vertex.index)
                        edge = self.celltype_graph.es[edge_id]
                        if conductance_name in edge.attribute_names():
                            if conductance_name == 'ggaba' and pretype_vertex['label'] == 'nRT' and posttype_vertex['label'] == 'TCR':
                                self.nRT_TCR_ggaba_low *= scale_factor
                                self.nRT_TCR_ggaba_high *= scale_factor
                                edge[conductance_name] = 'uniform %s %s' % (self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high)
                            else:
                                edge[conductance_name] *= scale_factor

                    except Exception, e:
                        pass

    def set_populations(self):
        """Read cellcounts from specified file and updates the
        celltype-graph accordingly. The file should have space
        separated values like:

        name count

        """
        config.LOGGER.debug('Updating cell counts')
        presynaptic_scaling = {}
        for celltype, count in config.runconfig.items('cellcount'):
            vertices = self.celltype_graph.vs.select(label_eq=celltype)
            for vertex in vertices:                
                presynaptic_scaling[celltype] = float(count) / vertex['count']
                vertex['count'] = int(count)
                config.LOGGER.info('%s population size: %d' % (celltype, vertex['count']))
        # presynaptic_scaling['TCR'] = 1.0 # Thu Jun  6 21:45:34 IST 2013 disabling scaling for TCR. 
        # <- Wed Oct  2 18:15:57 IST 2013 keep scaling for TCR.


        # 2012-05-07 18:24:53 (+0530) As discussed in last lab meet, I
        # need to scale the synaptic conductances according
        # reduction/increase in cell count of each type so that the
        # total conductance of each synapse type on each cell type
        # remains unchanged.
        for edge in self.celltype_graph.es:
            pre_vertex = self.celltype_graph.vs[edge.source]
            scale = presynaptic_scaling[pre_vertex['label']]
            if scale <= 0:
                continue
            edge['gampa'] = edge['gampa'] / scale
            try:
                edge['ggaba'] = edge['ggaba'] / scale
            except TypeError: # nRT->TCR is uniformly distributed between two values, scale those.
                tokens = edge['ggaba'].split()
                config.LOGGER.debug(str(tokens))
                self.nRT_TCR_ggaba_low = float(tokens[1]) / scale
                self.nRT_TCR_ggaba_high = float(tokens[2]) / scale
                edge['ggaba'] = 'uniform %s %s' % (self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high)

                config.LOGGER.debug('nRT->TCR after scaling ggaba %s: %g, %g' % (edge['ggaba'], self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high))
            edge['gnmda'] = edge['gnmda'] / scale
            config.LOGGER.info('scaled %s->%s conductances by %g' % (pre_vertex['label'], self.celltype_graph.vs[edge.target]['label'], 1.0/scale))
        
    def tweak_Ek(self, channel_class, value):
        """Adds value to channel's reversal potential. According
        Nernst equation, a multiplicative change in ionic
        concentration will cause an additive change in the reversal
        potential for that ion."""
        config.LOGGER.info('%s Ek += %g' % (channel_class.__name__, value))
        self.tweaks_doc.append('%s.Ek += %g' % (channel_class.__name__, value))
        for cell in self.cell_index_map.keys():
	    for ii in range(1, cell.num_comp+1):
                comp = cell.comp[ii]
                for chan in comp.channels:
                    if isinstance(chan, channel_class):
                        chan.Ek += value

    def set_unknown_prelease(self, value):
        self.tweaks_doc.append('prelease = 1.0 <- %g' % (value))
        for syn in self.celltype_graph.es:
            if syn['prelease'] == 1.0:
                syn['prelease'] = value

    def tune_conductances(self, filename):
        """Tune the conductances based on entries in file filename.
        file should have space separated entries like this:

        conductance-name sourcetype desttype scalefactor
        """
        if filename is None or self.from_netfile is not None:
            return        
        with open(filename) as synfile:
            for line in synfile.readlines():
                if line.strip().startswith('#'):
                    continue
                tokens = line.split()
                if not tokens:
                    continue
                [g_name, source, dest, scale_factor] = tokens                
                scale_factor = float(scale_factor)
                source_vertices = self.celltype_graph.vs.select(label_eq=source)
                dest_vertices = self.celltype_graph.vs.select(label_eq=dest)
                for src_v in source_vertices:
                    for dest_v in dest_vertices:
                        synid = self.celltype_graph.get_eid(src_v, dest_v)
                        if synid:
                            syn = self.celltype_graph.es[synid]
                            if g_name in syn.attribute_names():
                                if g_name == 'ggaba' and source == 'nRT' and dest == 'TCR':
                                    self.nRT_TCR_ggaba_low *= scale_factor
                                    self.nRT_TCR_ggaba_high *= scale_factor
                                    syn[g_name] = 'uniform %s %s' % (self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high)

                                else:
                                    syn[g_name] *= scale_factor
                                self.tweaks_doc.append('%s[%s->%s] *= %g' % (source, dest, scale_factor))

                                    
    def set_conductances(self, filename):
        """Set the conductances based on entries in file filename.
        file should have space separated entries like this:

        conductance-name sourcetype desttype value
        """
        if filename is None:
            return
        with open(filename) as synfile:
            for line in synfile.readlines():
                if line.strip().startswith('#'):
                    continue
                tokens = line.split()
                if not tokens:
                    continue
                [g_name, source, dest, value] = tokens
                value = float(value)
                source_vertices = self.celltype_graph.select(label_eq=source)
                dest_vertices = self.celltype_graph.select(label_eq=dest)
                for src_v in source_vertices:
                    for dest_v in dest_vertices:
                        synid = self.celltype_graph.get_eid(src_v, dest_v)
                        if synid:
                            syn = self.celltype_graph.es[synid]
                            if g_name in syn.attribute_names():
                                if g_name == 'ggaba' and source == 'nRT' and dest == 'TCR':
                                    self.nRT_TCR_ggaba_low = value
                                    self.nRT_TCR_ggaba_high = value
                                    syn[g_name] = 'uniform %s %s' % (self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high)
                                else:
                                    syn[g_name] = value

    def randomize_passive_properties(self):
        """Make the initial membrane potential of each cell deviate
        from the Em/Rm/Cm/Ra by sd as standard deviation. Where the
        sd's are assumed to be fractions of mean (the default values)."""
        config.LOGGER.debug('START Randomizing passive properties')
        initVm_sd = 0.0
        Rm_sd = 0.0
        Cm_sd = 0.0
        Ra_sd = 0.0
        Em_sd = 0.0
        try:
            initVm_sd = float(config.runconfig.get('sd_passive', 'initVm'))
            config.LOGGER.info('initVm randomized with sd=%g of standard value.' % (initVm_sd))
        except ConfigParser.NoOptionError:
            config.LOGGER.info('initVm constant in population.')
        try:
            Rm_sd = float(config.runconfig.get('sd_passive', 'Rm'))
            config.LOGGER.info('Rm randomized with sd=%g of standard value.' % (Rm_sd))
        except ConfigParser.NoOptionError:
            config.LOGGER.info('Rm constant in population.')
        try:
            Cm_sd = float(config.runconfig.get('sd_passive', 'Cm'))
            config.LOGGER.info('Cm randomized with sd=%g of standard value.' % (Cm_sd))
        except ConfigParser.NoOptionError:
            config.LOGGER.info('Cm constant in population.')
        try:
            Ra_sd = float(config.runconfig.get('sd_passive', 'Ra'))
            config.LOGGER.info('Ra randomized with sd=%g of standard value.' % (Ra_sd))
        except ConfigParser.NoOptionError:
            config.LOGGER.info('Ra constant in population')
        try:
            Em_sd = float(config.runconfig.get('sd_passive', 'Em'))
            config.LOGGER.info('Em randomized with sd=%g of standard value.' % (Em_sd))
        except ConfigParser.NoOptionError:
            config.LOGGER.info('Em constant in population.')
        for celltype in self.celltype_graph.vs:
            indices = self.populations[celltype['label']]
            if indices is None or len(indices) == 0:
                continue
            cell0 = self.index_cell_map[indices[0]]
            if cell0.soma.className != 'Compartment': # This is for spikegen replacing cells
                continue
            cells = [self.index_cell_map[index] for index in indices]
            if initVm_sd > 0.0:
                initVm_mean = cell0.soma.Em
                randomized_initVm = np.random.normal(loc=initVm_mean, scale=initVm_sd*np.abs(initVm_mean), size=len(indices))
                for ii in range(1, cell0.num_comp + 1):
                    assign_comp_param_to_population(cells, ii, 'initVm',  randomized_initVm)
            if Rm_sd > 0.0:
                # Make a list of Rm of all the compartments in this celltype.
                # These will be used as mean for the normal distribution for each compartment.
                mean_values = [(cell0.comp[ii].Rm, cell0.comp[ii].Cm, cell0.comp[ii].Ra) for ii in range(1, cell0.num_comp+1)]
                for ii in range(1, cell0.num_comp+1):
                    Rm_mean = cell0.comp[ii].Rm
                    randomized_Rm = np.random.normal(loc=mean_Rm, scale=Rm_sd * mean_Rm, size=len(indices))
                    assign_comp_param_to_population(cells, ii, 'Rm', randomized_Rm)
            if Cm_sd > 0.0:
                # Make a list of Cm of all the compartments in this celltype.
                # These will be used as mean for the normal distribution for each compartment.
                mean_values = [(cell0.comp[ii].Cm, cell0.comp[ii].Cm, cell0.comp[ii].Ra) for ii in range(1, cell0.num_comp+1)]
                for ii in range(1, cell0.num_comp+1):
                    Cm_mean = cell0.comp[ii].Cm
                    randomized_Cm = np.random.normal(loc=mean_Cm, scale=Cm_sd * mean_Cm, size=len(indices))
                    assign_comp_param_to_population(cells, ii, 'Cm', randomized_Cm)
            if Em_sd > 0.0:
                # Make a list of Em of all the compartments in this celltype.
                # These will be used as mean for the normal distribution for each cell.
                mean_Em = cell0.soma.Em
                randomized_Em = np.random.normal(loc=mean_Em, scale=Em_sd * np.abs(mean_Em), size=len(indices))
                for ii in range(1, cell0.num_comp + 1):
                    assign_comp_param_to_population(cells, ii, 'Em', randomized_Em)
            if Ra_sd > 0.0:
                # Make a list of Ra of all the compartments in this celltype.
                # These will be used as mean for the normal distribution for each compartment.
                mean_values = [(cell0.comp[ii].Ra, cell0.comp[ii].Ra, cell0.comp[ii].Ra) for ii in range(1, cell0.num_comp+1)]
                for ii in range(1, cell0.num_comp+1):
                    Ra_mean = cell0.comp[ii].Ra
                    randomized_Ra = np.random.normal(loc=mean_Ra, scale=Ra_sd * mean_Ra, size=len(indices))
                    assign_comp_param_to_population(cells, ii, 'Ra', randomized_Ra)
        config.LOGGER.debug('END Randomizing passive properties')


    def randomize_active_conductances(self):
        """Change the active conductances to be distributed normally
        around the original value with a standard deviation specified
        in the configuration file as a fraction of the original value."""
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Network loaded from %s' % (self.from_netfile))
            return
        config.LOGGER.debug('START randomize_active_conductances')
        conductance_dict = {}
        for conductance_name, value in config.runconfig.items('sd_active'):
            conductance_dict[conductance_name] = float(value)
        if not conductance_dict:
            return
        for celltype in self.celltype_graph.vs:
            indices = self.populations[celltype['label']]
            if not indices:
                continue
            cell0 = self.index_cell_map[indices[0]]
            if cell0.soma.className != 'Compartment': # Handle case of spikegen replacing cell
                continue 
            channels = []
            conductances = []
            for comp_no in range(1, cell0.num_comp+1):
                comp = cell0.comp[comp_no]
                chan_ids = moose.context.getWildcardList(comp.path + '/#[TYPE=HHChannel]', True)
                for chan_id in chan_ids:
                    proto_channel = moose.HHChannel(chan_id)
                    mean = proto_channel.Gbar
                    sd = proto_channel.Gbar * conductance_dict[proto_channel.name]
                    if mean <= 0.0 or sd <= 0.0:
                        continue
                    conductances = np.random.normal(loc=mean,
                                                       scale=sd,
                                                       size=len(indices))
                    conductances[conductances < 0] = mean # Subha: 2014-03-25 - avoid risk of negative conductance                
                    ii = 0
                    for index in indices:
                        cell = self.index_cell_map[index]
                        channel = moose.HHChannel(proto_channel.name, cell.comp[comp_no])
                        channel.Gbar = conductances[ii]
                        ii += 1
        config.LOGGER.debug('END randomize_active_conductances')

    def setup_bias_current(self, population_name, level, delay, width, data_container):
        """Apply a steady bias current to a population of cells.

        level, delay and width are either single values or lists of
        the same length.
        """
        pulsegen = moose.PulseGen('%s_bias' % (population_name), self.instrumentation)
        if isinstance(level, list):
            pulsegen.setCount(len(level)+1)
            for ii in range(len(level)):
                pulsegen.setLevel(ii, level[ii])
                pulsegen.setDelay(ii, delay[ii])
                pulsegen.setWidth(ii, width[ii])
            pulsegen.setDelay(len(level), 1e9) # last delay is set to infinite to avoid repetition
        else:
            pulsegen.setFirstLevel(level)
            pulsegen.setFirstWidth(width)
            pulsegen.setFirstDelay(delay)
        for cell_index in self.populations[population_name]:
            pulsegen.connect('outputSrc', self.index_cell_map[cell_index].soma, 'injectMsg')
        container = moose.Neutral('bias_current', data_container)
        pulsedata = moose.Table(pulsegen.name, container)
        pulsedata.stepMode = 3
        pulsedata.connect('inputRequest', pulsegen, 'output')
        config.LOGGER.info('Created pulsegen %s to apply bias current to %s population.' % (pulsegen.path, population_name))
    
    def save_cell_network(self, filename):
        """Save network model directly from MOOSE structure, rather
        than going through the graph-based version."""
        config.LOGGER.debug('START: save_cell_network to %s' % (filename))
        h5file =  h5.File(filename,  'w')
        h5file.attrs['TITLE'] = 'Traub Network: timestamp: %s' % (config.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        h5file.attrs['notes'] = '\n'.join(self.tweaks_doc)
        # Save simulation configuration data. I am saving it both in
        # data file as well as network file as often the data file is
        # too large and may not be available if the simulation is
        # cancelled midway.
        runconfig = h5file.create_group('runconfig')
        runconfig.attrs['TITLE'] = 'Simulation settings'
        for section in config.runconfig.sections():
            table_contents = config.runconfig.items(section)
            if table_contents:
                sectiontab = runconfig.create_dataset(section, data=np.rec.array(table_contents))
        
        # Save the celltype information (vertices of the celltype graph)
        network_struct =  h5file.create_group('network')
        network_struct.attrs['TITLE'] = 'Network structure'
        synapse_dtype = np.dtype([('source','S32'), 
                                     ('dest', 'S32'), 
                                     ('type', 'S4'), 
                                     ('Gbar', 'f4'),
                                     ('tau1', 'f4'), 
                                     ('tau2', 'f4'), 
                                     ('Ek', 'f4')])
        path_start = len('/model/net/')
        synchans = []
        conductances = []
        celltypes = []
        celltype_type = np.dtype([('name', 'S16'),
                                     ('index', 'i1'),
                                     ('count', 'i2')])
        for vertex in self.celltype_graph.vs:
            celltypes.append((vertex['label'], vertex.index, vertex['count']))
            for cell_index in self.populations[vertex['label']]:
                cell = self.index_cell_map[cell_index]
                for comp_index in range(1, cell.num_comp+1):
                    comp = cell.comp[comp_index]
                    for chan_id in moose.context.getChildren('%s/#[TYPE=HHChannel]' % (comp.path)):
                        chan = moose.HHChannel(chan_id)
                        conductances.append((chan.path, chan.Gbar, chan.Ek))
                        
                presyn_comp = cell.comp[cell.presyn]    
                if comp.className == 'Compartment':
                    spikegen = moose.SpikeGen('spike', presyn_comp)
                elif comp.className == 'SpikeGen':
                    spikegen = comp
                for synchan_id in spikegen.neighbours('event', moose.OUTGOING):
                    synchan = moose.SynChan(synchan_id)
                    post_comp = moose.Compartment(synchan.parent)
                    synchans.append((presyn_comp.path[path_start:], 
                                     post_comp.path[path_start:], 
                                     synchan.name.partition('_')[0], 
                                     synchan.Gbar,
                                     synchan.tau1,
                                     synchan.tau2,
                                     synchan.Ek))
        if conductances:
            dataset = np.rec.array(conductances)
            network_struct.create_dataset('hhchan', data=dataset)
        if synchans:
            dataset = np.rec.array(synchans, dtype=synapse_dtype)
            network_struct.create_dataset('synapse', data=dataset, compression='gzip')
        if celltypes:
            dataset = np.rec.array(celltypes, dtype=celltype_type)
            network_struct.create_dataset('celltype', data=dataset)
        stimulus_struct = h5file.create_group('stimulus')
        targets = []
        for stim in self.stim_container.children():
            for neighbour in config.context.getNeighbours(stim, 'outputSrc', moose.OUTGOING):
                print stim.path(), 'Stimulus to', neighbour.path()
                if moose.Neutral(neighbour).className == 'Compartment':
                    targets.append([stim.path(), neighbour.path()])
        if targets:
            dataset = stimulus_struct.create_dataset('connection', data=np.rec.array(targets))
        
        h5file.close()
        config.LOGGER.debug('END: save_cell_network')

    def save_network_model(self,  filename):
        """Save the network structure in an hdf5 file"""
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Network was loaded from file.')
            return
        config.LOGGER.debug('Start saving the network model')
        starttime =  datetime.now()
        compression_filter =  tables.Filters(complevel=9, complib='zlib', fletcher32=True)
        h5file =  tables.openFile(filename,  mode = 'w',  title = 'Traub Network: timestamp: %s' % (config.timestamp.strftime('%Y-%M-%d %H:%M:%S')),  filters = compression_filter)
        h5file.root._v_attrs.np_rngseed = config.numpy_rngseed
        h5file.root._v_attrs.moose_rngseed = config.moose_rngseed
        h5file.root._v_attrs.notes = '\n'.join(self.tweaks_doc)
        # Save simulation configuration data. I am saving it both in
        # data file as well as network file as often the data file is
        # too large and may not be available if the simulation is
        # cancelled midway.
        runconfig = h5file.createGroup(h5file.root, 'runconfig', 'Simulation settings')
        for section in config.runconfig.sections():
            table_contents = config.runconfig.items(section)
            if table_contents:
                sectiontab = h5file.createTable(runconfig, section, table_contents)        
        
        # Save the celltype information (vertices of the celltype graph)
        network_struct =  h5file.createGroup(h5file.root, 'network', 'Network structure')
        celltype_table =  h5file.createTable(network_struct, 'celltype', CellType,  'Information on each celltype population')
        celltype =  celltype_table.row
        for vertex in self.celltype_graph.vs:
            celltype['name'] =  vertex['label']
            celltype['index'] =  vertex.index
            celltype['count'] =  vertex['count']
            celltype.append()
        synapse_table = h5file.createTable(network_struct,  'synapsetype',  SynEdge, 'Synapse information between celltype pairs')
        synedge =  synapse_table.row
        for edge in self.celltype_graph.es:
            synedge['source'] = edge.source
            synedge['target'] =  edge.target
            synedge['weight'] = edge['weight']
            synedge['gampa'] = edge['gampa']
            synedge['gnmda'] = edge['gnmda']
            synedge['tauampa'] = edge['tauampa']
            synedge['taunmda'] = edge['taunmda']
            synedge['tau2nmda'] =  5e-3
            synedge['taugaba'] = edge['taugaba']
            synedge['prelease'] = edge['prelease']
            ii =  0
            pscomps = np.zeros(90, dtype=np.uint8)
            for pscomp in eval(edge['pscomps']): 
                pscomps[ii] = int(pscomp)
                ii +=  1
            synedge['pscomps'] = pscomps
            synedge['ekgaba'] = edge['ekgaba']
            # print edge.source, edge.target, edge['ggaba'], type(edge['ggaba'])

            it =  None
            try:
                it =  iter(edge['ggaba'])
            except TypeError:
                synedge['ggaba'] = np.array([edge['ggaba'], edge['ggaba']])

            assert ((it is None) or (self.celltype_graph.vs[edge.source]['label'] == 'nRT'))
            if self.celltype_graph.vs[edge.source]['label'] == 'nRT':
                if self.celltype_graph.vs[edge.target]['label'] == 'TCR':
                    synedge['ggaba'] =  np.array([self.nRT_TCR_ggaba_low, self.nRT_TCR_ggaba_high])
                synedge['taugabaslow'] = edge['taugabaslow']
            synedge.append()
        cellnet_group = h5file.createGroup(network_struct, 'cellnetwork', 'Cell-to-cell network structure')
        if self.g_ampa_mat.nnz > 0:
            gampa_array =  h5file.createCArray(cellnet_group, 'gampa', tables.FloatAtom(),  shape=(self.g_ampa_mat.nnz, 3))
            ii =  0
            for (index,  value) in self.g_ampa_mat.items():
                gampa_array[ii,0] = index[0]
                gampa_array[ii,1] =  index[1]
                gampa_array[ii,2] = value
                ii +=  1
        if self.g_nmda_mat.nnz > 0:
            gnmda_array =  h5file.createCArray(cellnet_group, 'gnmda', tables.FloatAtom(),  shape=(self.g_nmda_mat.nnz, 3))
            ii =  0
            for (index,  value) in self.g_nmda_mat.items():
                gnmda_array[ii,0] = index[0]
                gnmda_array[ii,1] =  index[1]
                gnmda_array[ii,2] = value
                ii +=  1
        if self.g_gaba_mat.nnz > 0:
            ggaba_array =  h5file.createCArray(cellnet_group, 'ggaba', tables.FloatAtom(),  shape=(self.g_gaba_mat.nnz, 3))
            ii =  0
            for (index,  value) in self.g_gaba_mat.items():
                ggaba_array[ii,0] = index[0]
                ggaba_array[ii,1] =  index[1]
                ggaba_array[ii,2] = value
                ii +=  1
        if self.ps_comp_mat.nnz > 0:
            pscomp_array =  h5file.createCArray(cellnet_group, 'pscomp',  tables.Int32Atom(),  shape=(self.ps_comp_mat.nnz, 3))
            ii =  0
            for (index,  value) in self.ps_comp_mat.items():
                pscomp_array[ii,0] = index[0]
                pscomp_array[ii,1] =  index[1]
                pscomp_array[ii,2] = value
                ii +=  1
        h5file.close()
        endtime =  datetime.now()
        delta =  endtime -  starttime
        config.BENCHMARK_LOGGER.info('Saved network model in:% g s' %  (delta.days *  86400 +  delta.seconds +  1e-6 * delta.microseconds))

    def verify_saved_model(self, filename):
        if self.from_netfile is not None:
            config.LOGGER.info('Do nothing. Model was loaded from network file')
            return
        starttime = datetime.now()
        h5file =  tables.openFile(filename)
        celltypes =  h5file.getNode('/network', name='celltype')
        for row in celltypes.iterrows():
            index =  row['index']
            assert self.celltype_graph.vs[index]['label'] == row['name']
            assert self.celltype_graph.vs[index]['count'] == row['count']
        synedges =  h5file.getNode('/network', 'synapsetype')
        for row in synedges.iterrows():
            source = row['source']
            target =  row['target']
            edge = self.celltype_graph.es[self.celltype_graph.get_eid(source, target)]
            assert row['ekgaba'] == edge['ekgaba']
            assert row['weight'] == edge['weight']
            assert row['gampa'] == edge['gampa']
            assert row['gnmda'] == edge['gnmda']
            assert row['tauampa'] == edge['tauampa']
            assert row['taunmda'] == edge['taunmda']
            assert row['tau2nmda'] ==  5e-3
            assert row['taugaba'] == edge['taugaba']
            ii =  0
            for pscomp in eval(edge['pscomps']): 
                try:
                    assert row['pscomps'][ii] == pscomp
                except AssertionError:
                    config.LOGGER.debug('pscomp not same: %s <> %s in synapse from %s to %s' % (row['pscomps'][ii], pscomp, self.celltype_graph.vs[source]['label'], self.celltype_graph.vs[target]))
                ii +=  1
            assert row['ekgaba'] == edge['ekgaba']

            it =  None
            try:
                it =  iter(edge['ggaba'])
            except TypeError:
                assert row['ggaba'][0] == edge['ggaba']
                assert row['ggaba'][0] == edge['ggaba']

            assert ((it is None) or (self.celltype_graph.vs[edge.source]['label'] == 'nRT'))
            if self.celltype_graph.vs[edge.source]['label'] == 'nRT':
                if self.celltype_graph.vs[edge.target]['label'] == 'TCR':
                    assert row['ggaba'][0] == self.nRT_TCR_ggaba_low
                    assert row['ggaba'][1] == self.nRT_TCR_ggaba_high
                assert row['taugabaslow'] == edge['taugabaslow']
        h5file.close()
        endtime = datetime.now()
        delta = endtime - starttime
        config.BENCHMARK_LOGGER.info('Finished verification of saved model in hdf5 in: %g s' % (delta.days * 86400 + delta.seconds + delta.microseconds * 1e-6))
        config.LOGGER.info('Verified model in: %s :: SUCCESS' %(filename))

    def read_network_model(self, filename):
        with h5.File(filename, 'r') as netf:
            self.read_cells(netf)
            self.update_hhchans_from_netfile(netf)
            self.create_synapses_from_netfile(netf)
            self.create_pulsegen_from_netfile(netf)
            self.from_netfile = filename

    def read_cells(self, netfile):
        start = datetime.now()
        cellcounts = np.sort(np.asarray(netfile['/network/celltype']), order='index')
        ci = 0 # cell index
        for row in cellcounts:
            ctype = row['name'] # Celltype
            count = row['count'] # Cell count
            cclass = eval(ctype) # Class object for the cell
            for ii in range(count):
                cell = cclass(cclass.prototype, '%s/%s_%d' % (self.network_container.path, ctype, ii))
                self.index_cell_map[ci] = cell
                self.cell_index_map[cell] = ci
                self.populations[ctype].append(ci) # populations maps celltype to the indices of the cells.
                ci += 1
        end = datetime.now()
        delta = end - start
        config.BENCHMARK_LOGGER.info('Time to read cell counts from file and to create %d cells: %g s' % (ci+1, 
                                                                                                          delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))

    def update_hhchans_from_netfile(self, netfile):
        start = datetime.now()
        chan_density = np.asarray(netfile['/network/hhchan'])        
        for row in chan_density:
            assert(config.context.exists(row[0]))
            chan = moose.HHChannel(row[0])
            chan.Gbar = row[1]
            chan.Ek = row[2]
        end = datetime.now()
        delta = end - start
        config.BENCHMARK_LOGGER.info('Time to update %d channels: %g s' % (len(chan_density), 
                                                                           delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))            

    def create_synapses_from_netfile(self, netfile):
        start = datetime.now()
        syninfo = np.asarray(netfile['/network/synapse'])
        nRT_gaba = defaultdict(dict)      
        for row in syninfo:
            # GABA synapses from nRT cells to thalamus have two
            # components - gaba_slow and gaba_fast and implemented as
            # two SynChan objects.
            # We store these for later
            if row['source'].startswith('nRT'):
                d = nRT_gaba[row['source']]
                if row['dest'] in d:
                    d[row['dest']].append(row)
                else:
                    d[row['dest']] = [row]
                continue
                    
            src = MyCompartment('%s/%s' % (self.network_container.path, row['source']))
            dst = MyCompartment('%s/%s' % (self.network_container.path, row['dest']))
            syntype = 'SynChan'
            if row['type'] == 'nmda':
                syntype = 'NMDAChan'
            delay = synapse.SYNAPTIC_DELAY_DEFAULT
            if (row['source'].startswith('nRT') or row['source'].startswith('TCR')):
                if not (row['dest'].startswith('nRT') or row['dest'].startswith('TCR')):
                    delay = synapse.SYNAPTIC_DELAY_THALAMOCORTICAL
            elif row['dest'].startswith('nRT') or row['dest'].startswith('TCR'):
                delay = synapse.SYNAPTIC_DELAY_CORTICOTHALAMIC
            name = '%s_from_%s' % (row['type'], row['source'].split('_')[0])
            config.LOGGER.debug('Creating %s with Ek=%g, type=%s' % (name, row['Ek'], type(row['Ek'])))            
            src.makeSynapse(dst,
                            classname=syntype,
                            name=name,
                            Ek=row['Ek'],
                            Gbar=row['Gbar'],
                            tau1=row['tau1'],
                            tau2=row['tau2'],
                            delay=delay)
        self.create_nRT_synapses(nRT_gaba)
        end = datetime.now()
        delta = end - start
        config.BENCHMARK_LOGGER.info('Time to create %d synapses: %g s' % (len(syninfo), 
                                                                           delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))   

    def create_nRT_synapses(self, nRT_gaba):
        """Special handling for GABA synapses from nRT cells which
        have a slow component."""
        for source, dest_dict in nRT_gaba.items():            
            for nRTsyn in dest_dict.values():
                print '####', nRTsyn
                if nRTsyn[0]['tau1'] > nRTsyn[1]['tau1']:
                    slow = nRTsyn[0]
                    regular = nRTsyn[1]
                else:
                    slow = nRTsyn[1]
                    regular = nRTsyn[0]
                src = MyCompartment('%s/%s' % (self.network_container.path, regular['source']))
                dst = MyCompartment('%s/%s' % (self.network_container.path, regular['dest']))
                delay = synapse.SYNAPTIC_DELAY_DEFAULT
                if not (regular['dest'].startswith('nRT') or regular['dest'].startswith('TCR')):
                    delay = synapse.SYNAPTIC_DELAY_THALAMOCORTICAL
                src.makeSynapse(dst,
                                classname='SynChan',
                                name='gaba_from_nRT',
                                Ek=regular['Ek'],
                                Gbar=regular['Gbar'],
                                tau1=regular['tau1'],
                                tau2=regular['tau2'],
                                delay=delay)
                src.makeSynapse(dst,
                                classname='SynChan',
                                name='gaba_slow_from_nRT',
                                Ek=slow['Ek'],
                                Gbar=slow['Gbar'],
                                tau1=slow['tau1'],
                                tau2=slow['tau2'],
                                delay=delay)
        

    def create_pulsegen_from_netfile(self, netfile):
        start = datetime.now()        
        self.create_stimulus_objects()        
        pg = np.asarray(netfile['/stimulus/connection'])
        bg_targets = []
        probe_targets = []
        for row in pg:
            config.LOGGER.info('Connecting %s to %s' % (row[0], row[1]))            
            if not moose.context.exists(row[0]):
                config.LOGGER.debug('Target does not exist: %s' % (row[0]))
                continue
            if not moose.context.exists(row[1]):
                config.LOGGER.debug('Target does not exist: %s' % (row[1]))
                continue
            if row[0].endswith('probe'):
                probe_targets.append(row[1])
            elif row[0].endswith('bg'):
                bg_targets.append(row[1])
            moose.PulseGen(row[0]).connect('outputSrc',
                                           moose.Compartment(row[1]),
                                           'injectMsg')
            config.LOGGER.info('Connected %s to %s' % (row[0], row[1]))
        self.restore_stimulus_settings_from_netfile(netfile)

        ret = { 'bg_targets': bg_targets,
                'probe_targets': probe_targets }

        end = datetime.now()
        delta = end - start
        config.BENCHMARK_LOGGER.info('Time to create stimuli: %g s' % (
                delta.days * 86400 + delta.seconds + 1e-6 * delta.microseconds))           
        return ret

    def restore_stimulus_settings_from_netfile(self, netfile, replicate=None):
        """Use the runconfig section in netfile to restore the
        stimulus settings. In case of randomized stimuli it does not
        ensure identical stimulus times.

        """
        datafilename = netfile.filename.replace('network', 'data').replace('.new','')
        with h5.File(datafilename, 'r') as df:
            cfg = dict(df['/runconfig/stimulus'])
            plotdt = float(dict(df['runconfig/scheduling'])['plotdt'])
            bg = np.asarray(df['/stimulus/stim_bg'])
            bgtimes = np.flatnonzero(np.diff(bg) > 0) * plotdt
            self.stim_bg = moose.PulseGen('/stim/stim_bg')
            self.stim_bg.count = len(bgtimes)
            delays = np.diff(np.r_[0.0, bgtimes])
            for index, t in enumerate(delays):
                self.stim_bg.delay[index] = t
                self.stim_bg.width[index] = float(cfg['pulse_width'])
                self.stim_bg.level[index] = float(cfg['amplitude'])
            probe = np.asarray(df['/stimulus/stim_probe'])
            probetimes = np.flatnonzero(np.diff(probe) > 0) * plotdt
            self.stim_probe = moose.PulseGen('/stim/stim_probe')
            self.stim_probe.count = len(probetimes+1)
            delays = np.diff(np.r_[0.0, probetimes])
            for index, t in enumerate(delays):
                self.stim_probe.delay[index] = t
                self.stim_probe.width[index] = float(cfg['pulse_width'])
                self.stim_probe.level[index] = float(cfg['amplitude'])
            # We have the absolute times of stimulus. Gate should be
            # turned on all the time - as if the bg and probe pulsegen were free running
            self.stim_gate.firstDelay = 0
        
    def create_stimulus_objects(self, stim_container='/stim', data_container='/data'):
        """Create the stimulus objects"""
        if  isinstance(stim_container, str):
            self.stim_container = moose.Neutral(stim_container)
        elif isinstance(stim_container, moose.Neutral):
            self.stim_container = stim_container
        else:
            raise Exception('Stimulus container must be a string or a Neutral object: got %s', stim_container.__class__.__name__)
        self.stim_gate = moose.PulseGen('stim_gate', self.stim_container)
        self.stim_gate.trigMode = moose.FREE_RUN
        self.stim_gate.firstWidth = 1e9 # Keep it on forever
        self.stim_gate.firstLevel = 1.0                
        self.stim_gate.secondDelay = 1e9
        self.stim_bg = moose.PulseGen('stim_bg', self.stim_container)
        self.stim_probe = moose.PulseGen('stim_probe', self.stim_container)
        self.stim_bg.trigMode = moose.EXT_GATE
        self.stim_probe.trigMode = moose.EXT_GATE
        self.stim_gate.connect('outputSrc', self.stim_bg, 'input')
        self.stim_gate.connect('outputSrc', self.stim_probe, 'input')
        if isinstance(data_container, str):
            data_container = moose.Neutral(data_container)
        stim_data_container = moose.Neutral('stimulus', data_container)
        gate_table = moose.Table(self.stim_gate.name, stim_data_container)
        gate_table.stepMode = 3
        gate_table.connect('inputRequest', self.stim_gate, 'output')
        bg_table = moose.Table(self.stim_bg.name, stim_data_container)
        bg_table.stepMode = 3
        bg_table.connect('inputRequest', self.stim_bg, 'output')
        probe_table = moose.Table(self.stim_probe.name, stim_data_container)
        probe_table.stepMode = 3
        probe_table.connect('inputRequest', self.stim_probe, 'output')

    def scale_synapses(self, filename):
        with open(filename) as synfile:
            for line in synfile.readlines():
                if line.strip().startswith('#'):
                    continue
                tokens = line.split()
                if not tokens:
                    continue
                [g_name, source, dest, scale_factor] = tokens                
                scale_factor = float(scale_factor)                
                for cell_index in self.populations[dest]:
                    cell = self.index_cell_map[cell_index]
                    if g_name.startswith('nmda'):
                        synchans = moose.context.getWildcardList(cell.path + '/##[ISA=NMDAChan]', True)
                    else:
                        synchans = moose.context.getWildcardList(cell.path + '/##[ISA=SynChan]', True)
                    for chanId in synchans:
                        chan = moose.HHChannel(chanId)
                        if chan.name.startswith(g_name) and chan.name.endswith('from_%s' % (source)):
                            chan.Gbar *= scale_factor
                self.tweaks_doc.append('%s[%s->%s] *= %g' % (chan.name, source, dest, scale_factor))
        

def test_generate_celltype_graph(celltype_file='celltype_graph.gml', format='gml'):
    celltype_graph = ig.read(celltype_file, format=format)
    trbnet = TraubNet()
    trbnet._generate_celltype_graph()
    for vertex in trbnet.celltype_graph.vs:
        original_vertex = celltype_graph.vs.select(label_eq=vertex['label'])
        assert original_vertex 
        assert original_vertex[0]['count'] == vertex['count']

    for edge in trbnet.celltype_graph.es:
        source = trbnet.celltype_graph.vs[edge.source]
        target = trbnet.celltype_graph.vs[edge.target]
        original_source = celltype_graph.vs.select(label_eq=source['label'])
        original_target = celltype_graph.vs.select(label_eq=target['label'])
        original_edge_id = celltype_graph.get_eid(original_source[0].index, original_target[0].index)
        original_edge = celltype_graph.es[original_edge_id]
        assert int(edge['weight'] * source['count']) == original_edge['weight']
        assert edge['gampa'] == original_edge['gampa']
        assert edge['gnmda'] == original_edge['gnmda']
        assert edge['tauampa'] == original_edge['tauampa']
        assert edge['taunmda'] == original_edge['taunmda']
        assert edge['taugaba'] == original_edge['taugaba']
        assert edge['pscomps'] == original_edge['pscomps']
        assert edge['ekgaba'] == original_edge['ekgaba']
        if source['label'] == 'nRT' and target['label'] == 'TCR':
            assert edge['taugabaslow'] == original_edge['taugabaslow']
            
def test_scale_conductance():
    netdata = TraubFullNetData()
    trbnet = TraubNet()
    trbnet._generate_celltype_graph()
    scale_dict_ampa = {('*', '*'): 2.0}
    scale_dict_nmda = {('*', 'SupLTS'): 0.2,
                       ('*', 'SupBasket'): 0.2,
                       ('*', 'SupAxoaxonic'): 0.2,
                       ('*', 'DeepLTS'): 0.2,
                       ('*', 'DeepBasket'): 0.2,
                       ('*', 'DeepAxoaxonic'): 0.2,
                       ('*', 'TCR'): 0.2,
                       ('*', 'nRT'): 0.2}
    scale_dict_ampa_ss_low = {('SpinyStellate', 'SpinyStellate'): 0.25/2.0}
    trbnet.scale_conductance('gampa', scale_dict_ampa)
    trbnet.scale_conductance('gnmda', scale_dict_nmda)
    trbnet.scale_conductance('gampa', scale_dict_ampa_ss_low)
    # TODO: now compare g's for each edge with the expected value
    for edge in trbnet.celltype_graph.es:
        source = trbnet.celltype_graph.vs[edge.source]
        target = trbnet.celltype_graph.vs[edge.target]
        src_index = netdata.celltype.index(source['label'])
        tgt_index = netdata.celltype.index(target['label'])
        gampa_baseline = netdata.g_ampa_baseline[src_index][tgt_index]
        gnmda_baseline = netdata.g_nmda_baseline[src_index][tgt_index]
        low_nmda_posttypes = [x[1] for x in scale_dict_nmda.keys()]
        if source['label'] == 'SpinyStellate' and target['label'] == 'SpinyStellate':
            assert np.allclose([edge['gampa']], [gampa_baseline * 0.25])
        else:
            assert np.allclose([edge['gampa']], [gampa_baseline * 2.0])
        if target['label'] in low_nmda_posttypes:
            assert np.allclose([edge['gnmda']], [gnmda_baseline * 0.2])
        else:
            assert np.allclose([edge['gnmda']], [gnmda_baseline])
    print 'test_scale_conductance: Successfully tested.'

def test_reading_network(filename):
    tn =  TraubNet()
    tn._generate_celltype_graph()
    tn._generate_cell_graph()
    h5file =  tables.openFile(filename)
    celltypes =  h5file.getNode('/network', name='celltype')
    for row in celltypes.iterrows():
        index =  row['index']
        assert tn.celltype_graph.vs[index]['label'] == row['name']
        assert tn.celltype_graph.vs[index]['count'] == row['count']
    synedges =  h5file.getNode('/network', 'synapsetype')
    for row in synedges.iterrows():
        source = row['source']
        target =  row['target']
        egde = tn.celltype_graph.es[tn.get_eid(source, target)]
        assert edge['ekgaba'] == edge['ekgaba']
        assert row['weight'] == edge['weight']
        assert row['gampa'] == edge['gampa']
        assert row['gnmda'] == edge['gnmda']
        assert row['tauampa'] == edge['tauampa']
        assert row['taunmda'] == edge['taunmda']
        assert row['tau2nmda'] ==  5e-3
        assert row['taugaba'] == edge['taugaba']
        ii =  0
        for pscomp in eval(edge['pscomps']): 
            assert row['pscomps'][ii] == pscomp
            ii +=  1
        assert row['ekgaba'] == edge['ekgaba']
        it =  None
        try:
            it =  iter(edge['ggaba'])
        except TypeError:
            assert row['ggaba'][0] == edge['ggaba']
            assert row['ggaba'][0] == edge['ggaba']
        assert ((it is None) or (self.celltype_graph.vs[edge.source]['label'] == 'nRT'))
        if self.celltype_graph.vs[edge.source]['label'] == 'nRT':
            if self.celltype_graph.vs[edge.target]['label'] == 'TCR':
                assert row['ggaba'][0] ==  tn.nRT_TCR_ggaba_low
                assert row['ggaba'][1] ==  tn.nRT_TCR_ggaba_high
            assert row['taugabaslow'] == edge['taugabaslow']
    h5file.close()

if __name__ == '__main__':
    # raise NotImplementedError('run trbsim.py in stead')
    net = TraubNet()
    # net.set_populations()
    net._generate_celltype_graph()
    net.celltype_graph.write('celltypegraph.graphml', format='graphml')
    # net._generate_cell_graph()
    # net.create_network()
    # net.save_network_model(config.MODEL_FILENAME)
    # net.verify_saved_model(config.MODEL_FILENAME)
    
# 
# trbnet.py ends here
