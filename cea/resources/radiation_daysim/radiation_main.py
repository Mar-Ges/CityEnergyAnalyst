"""
Radiation engine and geometry handler for CEA
"""
from __future__ import division
from __future__ import print_function

import os
import sys
import time
from itertools import repeat

import pandas as pd
from geopandas import GeoDataFrame as gpdf

import cea.config
import cea.inputlocator
from cea.datamanagement.databases_verification import verify_input_geometry_zone, verify_input_geometry_surroundings
from cea.resources.radiation_daysim import daysim_main, geometry_generator
from cea.resources.radiation_daysim.radiance import CEADaySim
from cea.utilities import epwreader
from cea.utilities.parallel import vectorize

__author__ = "Paul Neitzel, Kian Wee Chen"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Paul Neitzel", "Kian Wee Chen", "Jimeno A. Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


def reader_surface_properties(locator):
    """
    This function returns a dataframe with the emissivity values of walls, roof, and windows
    of every building in the scene

    :param cea.inputlocator.InputLocator locator: CEA InputLocator
    :returns pd.DataFrame: Dataframe with the emissivity values
    """

    # local variables
    architectural_properties = gpdf.from_file(locator.get_building_architecture())
    surface_database_windows = pd.read_excel(locator.get_database_envelope_systems(), "WINDOW")
    surface_database_roof = pd.read_excel(locator.get_database_envelope_systems(), "ROOF")
    surface_database_walls = pd.read_excel(locator.get_database_envelope_systems(), "WALL")

    # querry data
    df = architectural_properties.merge(surface_database_windows, left_on='type_win', right_on='code')
    df2 = architectural_properties.merge(surface_database_roof, left_on='type_roof', right_on='code')
    df3 = architectural_properties.merge(surface_database_walls, left_on='type_wall', right_on='code')
    fields = ['Name', 'G_win', "type_win"]
    fields2 = ['Name', 'r_roof', "type_roof"]
    fields3 = ['Name', 'r_wall', "type_wall"]
    surface_properties = df[fields].merge(df2[fields2], on='Name').merge(df3[fields3], on='Name')

    return surface_properties.set_index('Name').round(decimals=2)


def radiation_singleprocessing(cea_daysim, zone_building_names, locator, settings, geometry_pickle_dir, num_processes):

    weather_path = locator.get_weather_file()
    # check inconsistencies and replace by max value of weather file
    weatherfile = epwreader.epw_reader(weather_path)
    max_global = weatherfile['glohorrad_Whm2'].max()

    if settings.buildings == []:
        # get chunks of buildings to iterate
        chunks = [zone_building_names[i:i + settings.n_buildings_in_chunk] for i in
                  range(0, len(zone_building_names),
                        settings.n_buildings_in_chunk)]
    else:
        list_of_building_names = settings.buildings
        chunks = []
        for building_name in zone_building_names:
            if building_name in list_of_building_names:
                chunks.append([building_name])

    write_sensor_data = settings.write_sensor_data
    radiance_parameters = {"rad_ab": settings.rad_ab, "rad_ad": settings.rad_ad, "rad_as": settings.rad_as,
                           "rad_ar": settings.rad_ar, "rad_aa": settings.rad_aa,
                           "rad_lr": settings.rad_lr, "rad_st": settings.rad_st, "rad_sj": settings.rad_sj,
                           "rad_lw": settings.rad_lw, "rad_dj": settings.rad_dj,
                           "rad_ds": settings.rad_ds, "rad_dr": settings.rad_dr, "rad_dp": settings.rad_dp}
    grid_size = {"walls_grid": settings.walls_grid, "roof_grid": settings.roof_grid}

    num_chunks = len(chunks)
    if num_chunks == 1:
        for chunk_n, building_names in enumerate(chunks):
            daysim_main.isolation_daysim(
                chunk_n, cea_daysim, building_names, locator, radiance_parameters, write_sensor_data, grid_size,
                max_global, weatherfile, geometry_pickle_dir)
    else:
        vectorize(daysim_main.isolation_daysim, num_processes)(
            range(0, num_chunks),
            repeat(cea_daysim, num_chunks),
            chunks,
            repeat(locator, num_chunks),
            repeat(radiance_parameters, num_chunks),
            repeat(write_sensor_data, num_chunks),
            repeat(grid_size, num_chunks),
            repeat(max_global, num_chunks),
            repeat(weatherfile, num_chunks),
            repeat(geometry_pickle_dir, num_chunks)
        )


def check_daysim_bin_directory(path_hint):
    """
    Check for the Daysim bin directory based on ``path_hint`` and return it on success.

    If the binaries could not be found there, check in a folder `Depencencies/Daysim` of the installation - this will
    catch installations on Windows that used the official CEA installer.

    Check the RAYPATH environment variable. Return that.

    Check for ``C:\Daysim\bin`` - it might be there?

    If the binaries can't be found anywhere, raise an exception.

    :param str path_hint: The path to check first, according to the `cea.config` file.
    :return: path_hint, contains the Daysim binaries - otherwise an exception occurrs.
    """
    required_binaries = ["ds_illum", "epw2wea", "gen_dc", "oconv", "radfiles2daysim", "rtrace_dc"]
    required_libs = ["rayinit.cal", "isotrop_sky.cal"]

    def contains_binaries(path):
        """True if all the required binaries are found in path - note that binaries might have an extension"""
        try:
            found_binaries = set(bin for bin, _ in map(os.path.splitext, os.listdir(path)))
        except:
            # could not find the binaries, bogus path
            return False
        return all(bin in found_binaries for bin in required_binaries)

    def contains_libs(path):
        try:
            found_libs = set(os.listdir(path))
        except:
            # could not find the libs, bogus path
            return False
        return all(lib in found_libs for lib in required_libs)

    def contains_whitespace(path):
        """True if path contains whitespace"""
        return len(path.split()) > 1

    folders_to_check = [
        path_hint,
        os.path.join(os.path.dirname(sys.executable), "..", "Daysim"),
    ]
    # user might have a DAYSIM installation
    folders_to_check.extend(os.environ["RAYPATH"].split(";"))
    if sys.platform == "win32":
        folders_to_check.append(r"C:\Daysim\bin")
    folders_to_check = list(set(os.path.abspath(os.path.normpath(os.path.normcase(p))) for p in folders_to_check))

    for path in folders_to_check:
        if contains_binaries(path):
            # If path to binaries contains whitespace, provide a warning
            if contains_whitespace(path):
                print("ATTENTION: Daysim binaries found in '{}', but its path contains whitespaces. Consider moving the binaries to another path to use them.")
                continue

            if contains_libs(path):
                return str(path)
            else:
                # might be C:\Daysim\bin, try adding C:\Daysim\lib
                lib_path = os.path.abspath(os.path.normpath(os.path.join(path, "..", "lib")))
                if contains_libs(lib_path):
                    return str(path + os.pathsep + lib_path)

    raise ValueError("Could not find Daysim binaries - checked these paths: {}".format(", ".join(folders_to_check)))


def main(config):
    """
    This function makes the calculation of solar insolation in X sensor points for every building in the zone
    of interest. The number of sensor points depends on the size of the grid selected in the config file and
    are generated automatically.

    :param config: Configuration object with the settings (genera and radiation)
    :type config: cea.config.Configuartion
    :return:
    """

    #  reference case need to be provided here
    locator = cea.inputlocator.InputLocator(scenario=config.scenario)
    #  the selected buildings are the ones for which the individual radiation script is run for
    #  this is only activated when in default.config, run_all_buildings is set as 'False'

    # BUGFIX for #2447 (make sure the Daysim binaries are there before starting the simulation)
    config.radiation.daysim_bin_directory = check_daysim_bin_directory(config.radiation.daysim_bin_directory)

    # BUGFIX for PyCharm: the PATH variable might not include the daysim-bin-directory, so we add it here
    os.environ["PATH"] = "{bin}{pathsep}{path}".format(bin=config.radiation.daysim_bin_directory, pathsep=os.pathsep,
                                                       path=os.environ["PATH"])
    os.environ["RAYPATH"] = str(config.radiation.daysim_bin_directory)
    if not "PROJ_LIB" in os.environ:
        os.environ["PROJ_LIB"] = os.path.join(os.path.dirname(sys.executable), "Library", "share")
    if not "GDAL_DATA" in os.environ:
        os.environ["GDAL_DATA"] = os.path.join(os.path.dirname(sys.executable), "Library", "share", "gdal")

    print("verifying geometry files")
    zone_path = locator.get_zone_geometry()
    surroundings_path = locator.get_surroundings_geometry()
    print("zone: {zone_path}\nsurroundings: {surroundings_path}".format(zone_path=zone_path,
                                                                        surroundings_path=surroundings_path))
    verify_input_geometry_zone(gpdf.from_file(zone_path))
    verify_input_geometry_surroundings(gpdf.from_file(surroundings_path))

    # import material properties of buildings
    print("Getting geometry materials")
    building_surface_properties = reader_surface_properties(locator)
    building_surface_properties.to_csv(locator.get_radiation_materials())

    print("Creating 3D geometry and surfaces")
    geometry_pickle_dir = os.path.join(
        locator.get_temporary_folder(), "{}_radiation_geometry_pickle".format(config.scenario_name))
    print("Saving geometry pickle files in: {}".format(geometry_pickle_dir))
    # create geometrical faces of terrain and buildings
    geometry_terrain, zone_building_names, surroundings_building_names = geometry_generator.geometry_main(
        locator, config, geometry_pickle_dir)

    # daysim_bin_directory might contain two paths (e.g. "C:\Daysim\bin;C:\Daysim\lib") - in which case, only
    # use the "bin" folder
    bin_directory = [d for d in config.radiation.daysim_bin_directory.split(";") if not d.endswith("lib")][0]
    cea_daysim = CEADaySim(os.path.join(locator.get_temporary_folder(), 'cea_radiation'), bin_directory)

    # create radiance input files
    print("Creating radiance material file")
    cea_daysim.create_radiance_material(building_surface_properties)
    print("Creating radiance geometry file")
    cea_daysim.create_radiance_geometry(geometry_terrain, building_surface_properties, zone_building_names,
                                        surroundings_building_names, geometry_pickle_dir)

    print("Converting files for DAYSIM")
    weather_file = locator.get_weather_file()
    print('Transforming weather files to daysim format')
    cea_daysim.execute_epw2wea(weather_file)
    print('Transforming radiance files to daysim format')
    cea_daysim.execute_radfiles2daysim()

    time1 = time.time()
    radiation_singleprocessing(cea_daysim, zone_building_names, locator, config.radiation, geometry_pickle_dir,
                               num_processes=config.get_number_of_processes())

    print("Daysim simulation finished in %.2f mins" % ((time.time() - time1) / 60.0))


if __name__ == '__main__':
    main(cea.config.Configuration())
