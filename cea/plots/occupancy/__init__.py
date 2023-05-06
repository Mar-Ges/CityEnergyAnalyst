



import functools
import os

import pandas as pd

import cea.inputlocator

"""
Implements py:class:`cea.plots.OccupancyPlotBase` as a base class for all plots in the category "solar-potential"
and also set's the label for that category.
"""

__author__ = "Jimeno Fonseca"
__copyright__ = "Copyright 2023, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Jimeno Fonseca"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"

# identifies this package as a plots category and sets the label name for the category
label = 'Occupancy'

class OccupancyPlotBase(cea.plots.PlotBase):
    """Implements properties / methods used by all plots in this category"""
    category_name = "occupancy"

    expected_parameters = {
        'buildings': 'plots:buildings',
        'scenario-name': 'general:scenario-name',
        'timeframe': 'plots:timeframe',
        'normalization': 'plots:normalization',
    }

    def __init__(self, project, parameters, cache):
        super(OccupancyPlotBase, self).__init__(project, parameters, cache)
        self.category_path = os.path.join('new_basic', 'solar-potential')
        self.normalization = self.parameters['normalization']
        self.input_files = [(self.locator.get_schedule_model_file, [building]) for building in self.buildings]
        self.weather = self.locator.get_weather_file()
        self.schedule_analysis_fields = ['windows_east_kW',
                                      'windows_west_kW',
                                      'windows_south_kW',
                                      'windows_north_kW',
                                      'walls_east_kW',
                                      'walls_west_kW',
                                      'walls_south_kW',
                                      'walls_north_kW',
                                      'roofs_top_kW']


    def normalize_data(self, data_processed, buildings, analysis_fields):
        if self.normalization == "gross floor area":
            data = pd.read_csv(self.locator.get_total_demand()).set_index('Name')
            normalizatioon_factor = data.loc[buildings]['GFA_m2'].sum()
            data_processed = data_processed.apply(
                lambda x: x / normalizatioon_factor if x.name in analysis_fields else x)
        elif self.normalization == "net floor area":
            data = pd.read_csv(self.locator.get_total_demand()).set_index('Name')
            normalizatioon_factor = data.loc[buildings]['Aocc_m2'].sum()
            data_processed = data_processed.apply(
                lambda x: x / normalizatioon_factor if x.name in analysis_fields else x)
        elif self.normalization == "air conditioned floor area":
            data = pd.read_csv(self.locator.get_total_demand()).set_index('Name')
            normalizatioon_factor = data.loc[buildings]['Af_m2'].sum()
            data_processed = data_processed.apply(
                lambda x: x / normalizatioon_factor if x.name in analysis_fields else x)
        elif self.normalization == "building occupancy":
            data = pd.read_csv(self.locator.get_total_demand()).set_index('Name')
            normalizatioon_factor = data.loc[buildings]['people0'].sum()
            data_processed = data_processed.apply(
                lambda x: x / normalizatioon_factor if x.name in analysis_fields else x)
        return data_processed

    def add_fields(self, df1, df2):
        """Add the demand analysis fields together - use this in reduce to sum up the summable parts of the dfs"""
        fields = self.schedule_analysis_fields
        df1[fields] = df2[fields]
        return df1

    def resample_data(self):
        data = self._calculate_input_data_aggregated()
        data_normalized = self.normalize_data(data,
                                              self.buildings,
                                              self.schedule_analysis_fields)
        resampeled_data = self.resample_time_data(data_normalized)

        return resampeled_data

    def _calculate_input_data_aggregated(self):
        """This is the data all the solar-potential plots are based on."""
        # get extra data of weather and date
        result = functools.reduce(self.add_fields,
                                  (pd.read_csv(self.locator.get_schedule_model_file(building))
                                                     for building in self.buildings)).set_index('Date')

        return result
