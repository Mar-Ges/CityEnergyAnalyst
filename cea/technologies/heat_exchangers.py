"""
heat exchangers
"""


from __future__ import division
from math import log, ceil
import pandas as pd
import numpy as np
from cea.constants import HEAT_CAPACITY_OF_WATER_JPERKGK
from cea.technologies.constants import MAX_NODE_FLOW

__author__ = "Thuy-An Nguyen"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Thuy-An Nguyen", "Tim Vollrath", "Jimeno A. Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


# investment and maintenance costs

def calc_Cinv_HEX(Q_design_W, locator, config, technology_type):
    """
    Calculates the cost of a heat exchanger (based on A+W cost of oil boilers) [CHF / a]

    :type Q_design_W : float
    :param Q_design_W: Design Load of Boiler

    :param gv: globalvar.py

    :rtype InvC_return : float
    :returns InvC_return: total investment Cost in [CHF]

    :rtype InvCa : float
    :returns InvCa: annualized investment costs in [CHF/a]

    """
    if Q_design_W > 0:
        HEX_cost_data = pd.read_excel(locator.get_supply_systems(config.region), sheetname="HEX")
        HEX_cost_data = HEX_cost_data[HEX_cost_data['code'] == technology_type]
        # if the Q_design is below the lowest capacity available for the technology, then it is replaced by the least
        # capacity for the corresponding technology from the database
        if Q_design_W < HEX_cost_data.iloc[0]['cap_min']:
            Q_design_W = HEX_cost_data.iloc[0]['cap_min']
        HEX_cost_data = HEX_cost_data[
            (HEX_cost_data['cap_min'] <= Q_design_W) & (HEX_cost_data['cap_max'] > Q_design_W)]

        Inv_a = HEX_cost_data.iloc[0]['a']
        Inv_b = HEX_cost_data.iloc[0]['b']
        Inv_c = HEX_cost_data.iloc[0]['c']
        Inv_d = HEX_cost_data.iloc[0]['d']
        Inv_e = HEX_cost_data.iloc[0]['e']
        Inv_IR = (HEX_cost_data.iloc[0]['IR_%']) / 100
        Inv_LT = HEX_cost_data.iloc[0]['LT_yr']
        Inv_OM = HEX_cost_data.iloc[0]['O&M_%'] / 100

        InvC = Inv_a + Inv_b * (Q_design_W) ** Inv_c + (Inv_d + Inv_e * Q_design_W) * log(Q_design_W)

        Capex_a = InvC * (Inv_IR) * (1 + Inv_IR) ** Inv_LT / ((1 + Inv_IR) ** Inv_LT - 1)
        Opex_fixed = Capex_a * Inv_OM

    else:
        Capex_a = 0
        Opex_fixed = 0

    return Capex_a, Opex_fixed


def calc_Cinv_HEX_hisaka(network_info):
    """
    Calculates the cost of a heat exchanger (based on A+W cost of oil boilers) [CHF / a]

    :type Q_design_W : float
    :param Q_design_W: Design Load of Boiler

    :param gv: globalvar.py

    :rtype InvC_return : float
    :returns InvC_return: total investment Cost in [CHF]

    :rtype InvCa : float
    :returns InvCa: annualized investment costs in [CHF/a]

    """
    # read in nodes list
    all_nodes = pd.read_csv(network_info.locator.get_optimization_network_node_list_file(network_info.network_type,
                                                                                         network_info.network_name))

    # read in cost values from database
    HEX_prices = pd.read_excel(network_info.locator.get_supply_systems(network_info.config.region),
                               sheetname='HEX', index_col=0)
    a = HEX_prices['a']['District substation heat exchanger']
    b = HEX_prices['b']['District substation heat exchanger']
    c = HEX_prices['c']['District substation heat exchanger']
    d = HEX_prices['d']['District substation heat exchanger']
    e = HEX_prices['e']['District substation heat exchanger']
    Inv_IR = (HEX_prices['IR_%']['District substation heat exchanger']) / 100
    Inv_LT = HEX_prices['LT_yr']['District substation heat exchanger']
    Inv_OM = HEX_prices['O&M_%']['District substation heat exchanger'] / 100

    Capex_a = 0
    Opex_a_fixed = 0
    InvC = 0
    node_id_list = []
    #iterate through all buildings
    for building in network_info.building_names:
        cost = 0
        # check if building is connected to network
        if building not in network_info.building_names[network_info.disconnected_buildings_index]:
            # add HEX cost
            node_id = int(np.where(all_nodes['Building']==building)[0])
            node_id_list.append(all_nodes['Name'][node_id])
    # add plants to node id list
    plant_id_list = np.where(all_nodes['Type']=='Plant')[0]
    # find plant nodes
    for plant_id in plant_id_list:
        node_id_list.append('NODE'+str(plant_id))
    # read in mass flows
    for node_id in node_id_list:
        # read in node mass flows
        node_flows = pd.read_csv(network_info.locator.get_node_mass_flow_csv_file(network_info.network_type, network_info.network_name))
        # find design condition node mcp
        node_flow = max(node_flows[node_id])
        if node_flow > 0:
            # if the Q_design is below the lowest capacity available for the technology, then it is replaced by the least
            # capacity for the corresponding technology from the database
            mcp_sub = node_flow * HEAT_CAPACITY_OF_WATER_JPERKGK
            # Split into several HEXs if flows are too high
            if node_flow <= MAX_NODE_FLOW:
                cost = a + b * mcp_sub ** c + d * np.log(mcp_sub) + e * mcp_sub * np.log(mcp_sub)
            else:
                # we need to split into several HEXs
                cost = 0
                number_of_HEXs = int(ceil(node_flow / MAX_NODE_FLOW))
                nodeflow_nom = node_flow / number_of_HEXs
                mcp_sub = nodeflow_nom * HEAT_CAPACITY_OF_WATER_JPERKGK
                for i in range(number_of_HEXs):
                    ## calculate HEX losses
                    cost = cost + a + b * mcp_sub ** c + d * np.log(mcp_sub) + e * mcp_sub * np.log(mcp_sub)

            InvC = cost

            Capex_a = Capex_a + InvC * (Inv_IR) * (1 + Inv_IR) ** Inv_LT / ((1 + Inv_IR) ** Inv_LT - 1)
            Opex_a_fixed = Opex_a_fixed + InvC * Inv_OM

    return Capex_a, Opex_a_fixed
