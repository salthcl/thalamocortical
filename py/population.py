# population.py --- 
# 
# Filename: population.py
# Description: 
# Author: Subhasis Ray
# Maintainer: 
# Created: Thu Feb 18 22:00:46 2010 (+0530)
# Version: 
# Last-Updated: Fri Feb 19 03:13:30 2010 (+0530)
#           By: Subhasis Ray
#     Update #: 221
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

from collections import defaultdict
import csv 
import numpy

import moose
import allowedcomp
import config

class Population(moose.Neutral):
    """Homogeneous cell population - handles setting up connections
    between populations based on connection matrix.

    cell_class -- class name of cells contained in this population
    cell_list -- cells contained in this population

    """
    

    CELL_CONNECTION_MAP = None
    ALLOWED_COMP_MAP = None

    def __init__(self, path, cell_class, cell_count, prefix=None):
	"""Initialze the population by creating the cells.

	path -- path of this element as a container
	cell_class -- classobject for the cell type to be contained in
	this element.
	cell_count -- number of cells in this population
	prefix -- the n-th cell in this population gets the name {prefix}_{n}

	"""
	moose.Neutral.__init__(self, path)
        self.get_allowed_comp_map()
        self.get_connection_map()
	self.cell_list = []
	self.cell_type = cell_class.__name__
	if prefix is None:
	    prefix = self.cell_type
	for number in range(cell_count):
	    cell_name = '%s_%d' % (prefix, number)
	    cell_instance = cell_class(cell_class.prototype, self.path + '/' + cell_name)
	    self.cell_list.append(cell_instance)

    def connect(self, target):
        """Connect cells from this population to cells on the target
        population.        
        
        """
        config.LOGGER.debug(__name__ + ' starting')
        connection_map = self.get_connection_map()
        num_pre_per_post = connection_map[self.cell_type][target.cell_type]
        # This gets a 2_D matrix whose row[i] is the array of indices
        # of the pre-synaptic cells for i-th post-synaptic cell.
        precell_indices = numpy.random.randint(0, 
                                               high=len(self.cell_list), 
                                               size=(len(target.cell_list), num_pre_per_post))

        allowed_comp_map = self.get_allowed_comp_map()
        allowed_comp_list = numpy.array(allowed_comp_map[self.cell_type][target.cell_type])
        target_comp_indices = numpy.random.randint(0, 
                                                   high=len(allowed_comp_list), 
                                                   size=(len(target.cell_list), num_pre_per_post))
        for ii in range(len(target.cell_list)):
            target_comp_list = allowed_comp_list[target_comp_indices[ii]] # list containing the target compartment for each presynaptic cell
            for jj in range(num_pre_per_post):
                precell_index = precell_indices[ii][jj]
                precell = self.cell_list[precell_index]
                postcell = target.cell_list[ii]
                post_syn_comp_index = target_comp_list[jj]
                post_syn_comp = postcell.comp[post_syn_comp_index]
                pre_syn_comp = precell.comp[precell.presyn]
                config.LOGGER.debug('connecting: \t%s \tto \t%s' % (pre_syn_comp.path, post_syn_comp.path))

    def get_connection_map(self, filename='connmatrix.txt'):
	"""Load the celltype-to-celltype connectivity map from file
	and return a nested dictionary dict where dict[X][Y] is the
	number of presynaptic cells of type X connecting to each
	postsynaptic cell of type Y.

	filename -- the path of a csv file containing the connectivity
	matrix. The first row in the file should be the column headers
	- which are the cell types. The connection matrix itself is a
	square matrix with entry[i][j] specifying the number of
	presynaptic cells per postsynaptic cell, where the presynaptic
	cells are of type header[i] and the postsynaptic cell is of
	type header[j]

	"""
        if Population.CELL_CONNECTION_MAP is not None:
            return Population.CELL_CONNECTION_MAP
	config.LOGGER.debug('load_connection_map - loading connection matrix from ' + filename)
	connection_map = defaultdict(dict)
	reader = csv.reader(file(filename))
	header = reader.next()
	row = 0
	for line in reader:
	    if len(line) <= 0:
		continue
	    pre = header[row]  
	    row += 1
	    col = 0
	    for entry in line:
		post = header[col]
		value = int(entry)
		connection_map[pre][post] = value
		col += 1
        Population.CELL_CONNECTION_MAP = connection_map
	config.LOGGER.debug('load_connection_map - finished loading.')
	return connection_map
    
    def get_allowed_comp_map(self, filename=None):
	"""Load the tables for allowed compartment list for synapses
	between each types of cells. 
	
	Return a nested dictionary with entries like:
	entry["X"]["Y"] = [n1, n2, n3, n4, ...]

	where only compartments with index n1, n2, n3, .... are
	allowed as postsynaptic compartment for synapses from cells of
	type X to cells of type Y.

	filename -- the source of the map. A netcdf-4 file?

	"""
	# Right now I am compiling the Python interface for
	# netcdf4. Until it works, just use the raw python dictionary
        if Population.ALLOWED_COMP_MAP is not None:
            return Population.ALLOWED_COMP_MAP
        if filename is None:
            Population.ALLOWED_COMP_MAP = allowedcomp.ALLOWED_COMP
        else:
            raise Error, '%s - Loading allowed_compartment map from file is not yet implemented' % (__name__)
        return Population.ALLOWED_COMP_MAP
	

from spinystellate import SpinyStellate
# from suppyrRS import SupPyrRS

def test_main():
    pre = Population('/ss', SpinyStellate, 40)
    post = pre
    pre.connect(post)

if __name__ == '__main__':
    test_main()
# 
# population.py ends here
