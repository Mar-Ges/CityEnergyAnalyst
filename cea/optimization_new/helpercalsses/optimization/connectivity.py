"""
Connectivity Vector Class:
Connectivity Vectors are objects that contain information regarding the connection of buildings in the domain to the
available thermal networks.

E.g. let's assume there are 8 buildings in a district energy system which can be connected in up to 2 networks.
The corresponding connectivity vector contain 8 <Connection> objects (one per building) indicating which of the networks
each of the buildings are connected to in the given configuration:

network_connctions = [0, 1, 0, 0, 2, 1, 1, 2]
buildings = ['B1001', 'B1002', 'B1003', 'B1004', 'B1005', 'B1006', 'B1007', 'B1008']

The <ConnectivityVector>-class behaves like a sequence (which is relevant for some methods of the deap-library)
"""

__author__ = "Mathias Niffeler"
__copyright__ = "Copyright 2023, Cooling Singapore"
__credits__ = ["Mathias Niffeler"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "NA"
__email__ = "mathias.niffeler@sec.ethz.ch"
__status__ = "Production"

import random
from deap import tools

from cea.optimization_new.helpercalsses.optimization.fitness import Fitness
from cea.optimization_new.helpercalsses.optimization.clustering import Clustering


class Connection(object):
    possible_connections = range(0)
    possible_building_codes = []
    zero_demand_buildings = []

    def __init__(self, network_connection=None, building_code=None):
        self.building = building_code
        if network_connection:
            self.network_connection = network_connection
        else:
            self.network_connection = 0

    @property
    def network_connection(self):
        return self._network_connection

    @network_connection.setter
    def network_connection(self, new_connection):
        if new_connection and not isinstance(new_connection, int):
            raise ValueError(f"Network connection indicators need to be integer values. Tried to assign "
                             f"{new_connection}.")
        elif new_connection and not (new_connection in Connection.possible_connections):
            raise ValueError(f"The network connection indicator needs to be in the range "
                             f"[{Connection.possible_connections.start}, {Connection.possible_connections.stop - 1}]. "
                             f"Tried to assign {new_connection}.")
        elif self.building in Connection.zero_demand_buildings:
            self._network_connection = 0
        else:
            self._network_connection = new_connection

    @property
    def building(self):
        return self._building

    @building.setter
    def building(self, new_building_code):
        if new_building_code and not isinstance(new_building_code, str):
            raise ValueError(f"The connection indicators' corresponding building codes need to be of type string. "
                             f"Tried to assign {new_building_code}.")
        elif new_building_code and not (new_building_code in Connection.possible_building_codes):
            raise ValueError(f"The building code needs to be a valid identifier of one of the buildings withing the "
                             f"domain. Tried to assign {new_building_code}.")
        else:
            self._building = new_building_code

    @staticmethod
    def initialize_class_variables(domain):
        Connection.possible_connections = range(domain.config.optimization_new.maximum_number_of_networks + 1)
        Connection.possible_building_codes = [building.identifier for building in domain.buildings]
        Connection.zero_demand_buildings = [building.identifier for building in domain.buildings
                                            if all(building.demand_flow.profile == 0)]


class ConnectivityVector(object):
    _cluster_indexes: list = None

    def __init__(self, connection_list=None):
        if not connection_list:
            self.connections = [Connection()]
        else:
            self.connections = connection_list
        self.fitness = Fitness()

    @property
    def connections(self):
        return self._connections

    @connections.setter
    def connections(self, new_connections):
        if not (isinstance(new_connections, list) and
                all([isinstance(connection, Connection) for connection in new_connections])):
            raise ValueError("The initialisation of a new connectivity vector requires a list of 'Connection'-objects.")
        else:
            # Check if any of the network connection values appear only once...
            new_values = [new_connection.network_connection for new_connection in new_connections]
            values_appearing_once = [i for i in Connection.possible_connections if new_values.count(i) == 1]

            # ... if so set them to 0 (network with only one building = stand-alone building)
            if values_appearing_once:
                changed_values = {i: 0 for i, connection in enumerate(new_connections)
                                  if connection.network_connection in values_appearing_once}
                for index, corrected_value in changed_values.items():
                    new_connections[index].network_connection = corrected_value

            # Set the connectivity vector
            self._connections = new_connections

    @property
    def values(self):
        network_connection_values = tuple(connection.network_connection for connection in self.connections)
        return network_connection_values

    @values.setter
    def values(self, new_values):
        if not (isinstance(new_values, list) and len(new_values) == len(self)):
            raise ValueError("To assign new network connection indicator values they need to be given as a list of "
                             "the same length as the connectivity vector.")
        else:
            # Check if any of the network connection values appear only once...
            values_appearing_once = [i for i in Connection.possible_connections if new_values.count(i) == 1]

            # ... if so set them to 0 (network with only one building = stand-alone building)
            if values_appearing_once:
                new_values = [0 if i in values_appearing_once else i for i in new_values]

            # Set the new values
            for i in range(len(self)):
                self[i] = new_values[i]

    @property
    def fitness(self):
        return self._fitness

    @fitness.setter
    def fitness(self, new_fitness):
        if not isinstance(new_fitness, Fitness):
            raise ValueError("The indicated fitness value is not an object of the Fitness class. The deap library's "
                             "selection functions need the attributes of that class to operate properly.")
        else:
            self._fitness = new_fitness

    def __hash__(self):
        return hash(self.values)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.values == other.values

    def __len__(self):
        return len(self.connections)

    def __getitem__(self, item):
        if isinstance(item, slice):
            selected_connections = self._connections[item]
            return [connection.network_connection for connection in selected_connections]
        elif isinstance(item, int):
            return self.connections[item].network_connection
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            if key.start:
                ind_start = key.start
            else:
                ind_start = 0
            if key.stop:
                ind_stop = key.stop
            else:
                ind_stop = len(self)
            if key.step:
                ind_step = key.step
            else:
                ind_step = 1
            for index in list(range(ind_start, ind_stop, ind_step)):
                self.connections[index].network_connection = round(value[index-ind_start], 2)
        elif isinstance(key, int):
            self.connections[key].network_connection = round(value, 2)

    def reset(self):
        """
        Reset the entire connectivity vector at once in order to correct connectivity values (checked in the setter)
        after mutation or recombination.
        e.g. if only one building is connected to any given network, i.e. it is really a stand-alone building)
        """
        self.connections = self.connections

        return self

    def as_str(self):
        """
        Return the capacity indicator vector as single string-object (network connection values spaced by an underscore)
        """
        connectivity_str = '_'.join(map(str, self.values))
        return connectivity_str

    @staticmethod
    def generate(method='random'):
        """
        Generate a new list of <Connection>-class objects with random network-connection values in [0, nbr_networks].
        """
        if method == 'random':
            min_connection_ind = Connection.possible_connections.start
            max_connection_ind = Connection.possible_connections.stop - 1
            connections_list = [Connection(random.randint(min_connection_ind, max_connection_ind), building)
                                for building in Connection.possible_building_codes]
        else:
            connections_list = [Connection(0, building) for building in Connection.possible_building_codes]
        return connections_list

    @staticmethod
    def mutate(cv, algorithm=None, connection_points:list=None):
        """
        Mutate the connectivity vector (inplace) according to the defined mutation algorithm.
        :param cv: ConnectivityVector object to be mutated
        :param algorithm: Genetic algorithm settings to be used
        :param connection_points: List of connection points (needed for the ClusterSwitch mutation)
        """
        if algorithm.mutation == 'ShuffleIndexes':
            mutated_cv = tools.mutShuffleIndexes(cv, algorithm.mut_prob)
        elif algorithm.mutation == 'UniformInteger':
            nbr_of_networks = Connection.possible_connections.stop - 1
            mutated_cv = tools.mutUniformInt(cv, low=0, up=nbr_of_networks, indpb=algorithm.mut_prob)
        elif algorithm.mutation == 'ClusterSwitch':
            if not ConnectivityVector._cluster_indexes:
                ConnectivityVector._cluster_indexes = Clustering(connection_points).cluster()
            mutated_cv = ConnectivityVector.ClusterSwitch(cv, algorithm.mut_prob)
        else:
            raise ValueError(f"The chosen mutation method ({algorithm.mutation}) has not been implemented for "
                             f"connectivity vectors.")

        # reset to correct potential format of the connectivity vector
        mutated_cv[0].reset()

        return mutated_cv

    @staticmethod
    def ClusterSwitch(cv, mut_prob:float):
        """
        Mutate the connectivity vector (inplace) by switching all switching buildings in the same cluster to a random
        other connectivity value with a probability of mut_prob.
        Outliers are switched with the same probability but individually (new random value chosen for each outlier).
        :param cv: Connectivity vector to be mutated
        :param mut_prob: Probability of mutation
        """
        # Identify clusters and possible connectivity values
        clusters = list(set(ConnectivityVector._cluster_indexes))
        possible_connections = list(Connection.possible_connections)

        # Switch building connectivity values cluster-wise
        for cluster in clusters:
            # Switch all buildings in the same cluster to the same connectivity value
            if cluster >= 0:
                new_connectivity = random.choice(possible_connections)
                for i, cluster_index in enumerate(ConnectivityVector._cluster_indexes):
                    if cluster_index == cluster:
                        if random.random() < mut_prob:
                            cv[i] = new_connectivity
            # Switch outliers individually
            else:
                for i, cluster_index in enumerate(ConnectivityVector._cluster_indexes):
                    if cluster_index < 0:
                        if random.random() < mut_prob:
                            cv[i] = random.choice(possible_connections)
                            
        return cv

    @staticmethod
    def mate(cv_1, cv_2, algorithm=None, connection_points:list=None):
        """
        Recombine two connectivity vectors (inplace) according to the defined crossover algorithm.
        :param cv_1: First connectivity vector
        :param cv_2: Second connectivity vector
        :param algorithm: Algorithm object containing the crossover method and probability
        :param connection_points: List of all connection points in the network
        """
        if algorithm.crossover == 'OnePoint':
            recombined_cvs = tools.cxOnePoint(cv_1, cv_2)
        elif algorithm.crossover == 'TwoPoint':
            recombined_cvs = tools.cxTwoPoint(cv_1, cv_2)
        elif algorithm.crossover == 'Uniform':
            recombined_cvs = tools.cxUniform(cv_1, cv_2, algorithm.cx_prob)
        elif algorithm.crossover == 'ClusterSwap':
            if not ConnectivityVector._cluster_indexes:
                ConnectivityVector._cluster_indexes = Clustering(connection_points).cluster()
            recombined_cvs = ConnectivityVector.ClusterSwap(cv_1, cv_2, algorithm.cx_prob)
        elif algorithm.crossover == 'ClusterAlignment':
            if not ConnectivityVector._cluster_indexes:
                ConnectivityVector._cluster_indexes = Clustering(connection_points).cluster()
            recombined_cvs = ConnectivityVector.ClusterAlignment(cv_1, cv_2, algorithm.cx_prob)
        else:
            raise ValueError(f"The chosen crossover method ({algorithm.crossover}) has not been implemented for "
                             f"connectivity vectors.")

        # reset to correct potential error in format of the connectivity vectors
        recombined_cvs[0].reset()
        recombined_cvs[1].reset()

        return recombined_cvs

    @staticmethod
    def ClusterSwap(cv_1, cv_2, cx_prob):
        """
        Recombine two connectivity vectors by exchanging the connectivity values of some of their clusters. Outliers
        remain unchanged by this operation.
        :param cv_1: connectivity vector 1
        :param cv_2: connectivity vector 2
        :param cx_prob: probability of exchanging the connectivity values of a cluster
        """
        # determine which clusters to swap
        clusters = list(set(ConnectivityVector._cluster_indexes))
        selected_clusters = ConnectivityVector.select_values_with_probability(clusters, cx_prob)

        # swap the connectivity values of the selected clusters
        for cluster in selected_clusters:
            cluster_indexes = [i for i, x in enumerate(ConnectivityVector._cluster_indexes) if x == cluster]
            for index in cluster_indexes:
                cv_1[index], cv_2[index] = cv_2[index], cv_1[index]

        return cv_1, cv_2

    @staticmethod
    def select_values_with_probability(values:list, probability:float):
        """
        Select a value from a list of values with a given probability.
        """
        selected_values = []
        for value in values:
            if random.random() < probability:
                selected_values.append(value)
        return selected_values

    @staticmethod
    def ClusterAlignment(cv_1, cv_2, cx_prob):
        """
        Recombine two connectivity vectors by exchanging the connectivity values of the buildings where:
         1. they deviate from the most prevalent connectivity value of the cluster they belong to and
         2. a swap of the connectivity value between the two connectivity vectors would align them with the most
            prevalent connectivity value of their cluster.

        e.g. if building b is connected to network 1 in cv_1 whereas the most prevalent connectivity value of b's
        cluster is 0 in cv_1 and building b is unconnected (i.e. has a connectivity value of 0) in cv_2 whereas
        the most prevalent connectivity in its cluster is 1 in cv_2, then the connectivity values of b in cv_1 and cv_2
        are swapped.

        Outliers remain unchanged by this operation.
        """
        # determine the most prevalent connectivity value for each cluster in cv_1 and cv_2
        clusters = list(set(ConnectivityVector._cluster_indexes))
        prevailing_connectivity_values_1 = ConnectivityVector._get_most_prevalent_connectivity_values(cv_1, clusters)
        prevailing_connectivity_values_2 = ConnectivityVector._get_most_prevalent_connectivity_values(cv_2, clusters)

        # determine buildings for which the connectivity values in cv_1 matches the most prevalent connectivity value of
        # their cluster in cv_2 and vice-versa
        swappable_building_indexes = [i for i, (pcv_1, pcv_2) in enumerate(zip(prevailing_connectivity_values_1,
                                                                               prevailing_connectivity_values_2))
                                      if cv_1[i] == pcv_2 and cv_2[i] == pcv_1]

        # chose buildings to swap
        buildings_to_swap = ConnectivityVector.select_values_with_probability(swappable_building_indexes, cx_prob)

        # change the connectivity values of the selected buildings
        for building in buildings_to_swap:
            cv_1[building], cv_2[building] = cv_2[building], cv_1[building]

        return cv_1, cv_2

    @staticmethod
    def _get_most_prevalent_connectivity_values(cv, clusters):
        """
        Determine the most prevalent connectivity value for each cluster in cv and return a list that contains that
        value for each building's corresponding cluster. Ignore outliers (i.e. buildings that are not part of a
        cluster).
        """
        most_prevalent_connectivity_values = [None] * len(cv)
        for cluster in clusters:
            if cluster < 0:
                continue
            relevant_building_indexes = [i for i, x in enumerate(ConnectivityVector._cluster_indexes) if x == cluster]
            building_connectivity_values = [cv[i] for i in relevant_building_indexes]
            most_prevalent_connectivity_value = max(set(building_connectivity_values),
                                                    key=building_connectivity_values.count)
            for index in relevant_building_indexes:
                most_prevalent_connectivity_values[index] = most_prevalent_connectivity_value

        return most_prevalent_connectivity_values

    @staticmethod
    def select(individuals_list, energy_system_solutions_dict, population_size, optimization_tracker=None):
        """
        Select the 'best' connectivity vectors by performing 'non-dominated sorting' (NSGA) on their respective energy
        system solutions; where the energy system solutions are given by the 'best' combinations of the supply systems
        for each of the networks given by the connectivity vectors.

        :param individuals_list: list of the investigated connectivity vectors
        :type individuals_list: list of <ConnectivityVector>-class objects
        :param energy_system_solutions_dict: A set of non-dominated energy system solutions for each connectivity vector.
                                             Each energy system solution is a combination of supply systems for each
                                             network + supply systems for each stand-alone building. Non-domination is
                                             determined based on selected objectives for the optimisation.
        :type energy_system_solutions_dict: dict of lists of <deap.creator.SystemCombination>-class objects
                                            (defined in cea.optimization_new.districtEnergySystem.py)
        :param population_size: number of individuals to be selected as the population of the next interation
        :type population_size: int
        :param optimization_tracker: object tracking the progress of the optimization
        :type optimization_tracker: <cea.optimization_new.helperclasses.optimization.tracker>-OptimizationTracker class
                                    object
        """
        # create a dictionary associating the connectivity 'str'-expression to the corresponding objects
        individual_dict = {ind.as_str(): ind for ind in individuals_list}

        # combine all energy system solutions (i.e. supply system combinations) in one large list
        all_supsys_combinations = sum(energy_system_solutions_dict.values(), start=[])
        nbr_solutions = len(all_supsys_combinations)

        # perform non-dominated sorting on the list of energy system solutions and identify which connectivity-vector's
        # solutions appear in which front (i.e. order of non-dominated front)
        supsys_combination_solution_fronts = tools.emo.sortLogNondominated(all_supsys_combinations, nbr_solutions)
        connectivity_vectors_by_front = {front: list(set([supsys_combination.encoding[0]
                                                          for supsys_combination in solutions_in_front]))
                                         for front, solutions_in_front in enumerate(supsys_combination_solution_fronts)}

        # select a new population of 'best' connectivity vectors
        new_population = []
        for front in connectivity_vectors_by_front.values():
            if len(new_population) >= population_size:
                break

            for connectivity_vector in front:
                if len(new_population) >= population_size:
                    break

                if connectivity_vector in individual_dict.keys():
                    new_population += [individual_dict[connectivity_vector]]
                    del individual_dict[connectivity_vector]

        if optimization_tracker:
            optimization_tracker.update_current_non_dominated_fronts(new_population, supsys_combination_solution_fronts)

        return new_population
