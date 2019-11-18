"""
This is a template script - an example of how a CEA script should be set up.

NOTE: ADD YOUR SCRIPT'S DOCUMENTATION HERE (what, why, include literature references)
"""
from __future__ import division
from __future__ import print_function

import os
import cea.config
import cea.inputlocator
import pandas as pd
from sklearn.metrics import mean_squared_error
from math import sqrt
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import seaborn as sns


__author__ = "Luis Santos"
__copyright__ = "Copyright 2018, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Luis Santos, Jimeno Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


def template(locator, archetypes):
    """this is where the action happens if it is more than a few lines in ``main``.
    NOTE: ADD YOUR SCRIPT'S DOCUMENATION HERE (how)
    NOTE: RENAME THIS FUNCTION (SHOULD PROBABLY BE THE SAME NAME AS THE MODULE)
    """
    annual = False
    monthly = True

    if annual == True:
        print("annual validation")
        # extract real data and model output
        measurements_path = locator.get_measurements()
        annual_real_data= pd.read_csv(measurements_path + '/annual_measurements.csv')
        real_names = annual_real_data.Name

        demand_path = locator.get_demand_results_folder()
        annual_model_data = pd.read_csv(demand_path + '/Total_demand.csv')
        model_names = annual_model_data.Name

        merged_annual = annual_model_data.merge(annual_real_data, how='inner', on=['Name'])
        model = merged_annual.GRID_MWhyr
        real = merged_annual.Ec_measured

        # calculate errors
        MBE_annual = ((model - real)/model )*100
        print(MBE_annual)


    if monthly == True:
        print("monthly validation")
        # extract real data
        measurements_path = locator.get_measurements()
        monthly_real_data= pd.read_csv(measurements_path + '/monthly_measurements.csv')
        real_names = monthly_real_data.Name.values[0]

        # extract model output
        demand_path = locator.get_demand_results_folder()
        monthly_model_data = str(demand_path) + "\\" + str(real_names) + '.csv'
        model = pd.read_csv(monthly_model_data)
        idx = pd.to_datetime(model.DATE)
        model['datetime'] = idx
        model_monthly = model.resample('M', on = 'datetime').sum()
        monthly_model_data = [model_monthly.GRID_kWh]
        monthly_model_data = pd.DataFrame(monthly_model_data)


        # hours = test.groupby(test.DATE.str[5:7])
        #

        # # annual_model_data = pd.read_csv(demand_path + '/Total_demand.csv')
        # # model_names = annual_model_data.Name
        # #
        # # merged_annual = annual_model_data.merge(annual_real_data, how='inner', on=['Name'])
        # # model = merged_annual.GRID_MWhyr
        # # real = merged_annual.Ec_measured
        # #
        # #
        # # # calculate errors
        # #
        # # NMBE_annual = ((model - real)/model )*100
        # # # CvRMSE_annual = (math.sqrt((model - real)**2) / model)*100
        # # print(NMBE_annual)
        # # print(CvRMSE_annual)
        real_data = monthly_real_data.loc[:,'Ec_m1':'Ec_m12']
        real_data = real_data.values
        model_data = monthly_model_data.values
        be = real_data - model_data
        nmbe =be.sum()/real_data.mean()
        print(nmbe)
        mse = mean_squared_error(real_data,model_data)
        rmse = sqrt(mse)
        cvrmse = rmse*100
        print(cvrmse)

        # print (math.sqrt(9))
        # print (real_names.dtypes)

        # for i in range(1,13):
        #    print('Ec_m'+str(i))
        #    print (monthly_real_data.(i))
    pass


def main(config):
    """
    This is the main entry point to your script. Any parameters used by your script must be present in the ``config``
    parameter. The CLI will call this ``main`` function passing in a ``config`` object after adjusting the configuration
    to reflect parameters passed on the command line - this is how the ArcGIS interface interacts with the scripts
    BTW.

    :param config:
    :type config: cea.config.Configuration
    :return:
    """
    assert os.path.exists(config.scenario), 'Scenario not found: %s' % config.scenario
    locator = cea.inputlocator.InputLocator(config.scenario)

    template(locator, config.scenario)


if __name__ == '__main__':
    main(cea.config.Configuration())