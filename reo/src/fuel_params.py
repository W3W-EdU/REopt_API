# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NREL/REopt_API/blob/master/LICENSE.
import os
import operator
import calendar
import numpy
import logging
from reo.utilities import MMBTU_TO_KWH, GAL_DIESEL_TO_KWH
log = logging.getLogger(__name__)

class FuelParams:
    """
    Sub-function of DataManager.

    Used for fuel burning parameters, fuel cost, and CHP thermal production and power derate

    """
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    def __init__(self, big_number, elec_tariff, fuel_tariff, generator=None):
        self.big_number = big_number
        self.time_steps_per_hour = elec_tariff.time_steps_per_hour

        # Assign monthly fuel rates for boiler and chp and then convert to timestep intervals
        self.boiler_fuel_blended_monthly_rates_us_dollars_per_mmbtu = fuel_tariff.monthly_rates('boiler')
        self.chp_fuel_blended_monthly_rates_us_dollars_per_mmbtu = fuel_tariff.monthly_rates('chp')
        self.newboiler_fuel_blended_monthly_rates_us_dollars_per_mmbtu = fuel_tariff.monthly_rates('newboiler')
        self.boiler_fuel_rate_array = []
        self.chp_fuel_rate_array = []
        self.newboiler_fuel_rate_array = []
        for month in range(0, 12):
            # Create full length (timestep) array of NG cost, converting $/MMBtu to $/kWh
            self.boiler_fuel_rate_array.extend([self.boiler_fuel_blended_monthly_rates_us_dollars_per_mmbtu[month] / MMBTU_TO_KWH] * 
                                                self.days_in_month[month] * 24 * self.time_steps_per_hour)
            self.chp_fuel_rate_array.extend([self.chp_fuel_blended_monthly_rates_us_dollars_per_mmbtu[month] / MMBTU_TO_KWH] *
                                                self.days_in_month[month] * 24 * self.time_steps_per_hour)
            self.newboiler_fuel_rate_array.extend([self.newboiler_fuel_blended_monthly_rates_us_dollars_per_mmbtu[month] / MMBTU_TO_KWH] * 
                                                self.days_in_month[month] * 24 * self.time_steps_per_hour)
        if generator is not None:
            self.generator_fuel_rate_array = [generator.diesel_fuel_cost_us_dollars_per_gallon / GAL_DIESEL_TO_KWH for
                                              _ in range(8760 * self.time_steps_per_hour)]

    def _get_fuel_burning_tech_params(self, techs, generator=None, chp=None):
        """
        In the Julia model we have:
         - d["FuelCost"] = vector_to_axisarray(d["FuelCost"], d["FuelType"], d[:TimeStep])
         - d["FuelLimit"] = AxisArray(d["FuelLimit"], d["FuelType"])
         - FuelType::Array{String,1}
         - d["TechsByFuelType"] = AxisArray(d["TechsByFuelType"], d["FuelType"])
        :return: fuel_costs, fuel_limit, fuel_types, techs_by_fuel_type (all lists)
        """

        fuel_costs = []
        fuel_burn_slope = []
        fuel_burn_intercept = []
        fuel_limit = []
        fuel_types = []
        techs_by_fuel_type = []

        for tech in techs:
            # Assign fuel_costs, fuel_burn_slope, fuel_burn_intercept, fuel_limit, techs_by_fuel_type, and fuel_types,
            # Convert fuel basis to kWh if not already
            if tech.lower() == 'generator':
                # generator fuel is not free anymore since generator is also a design variable
                fuel_costs = operator.add(fuel_costs, self.generator_fuel_rate_array)
                fuel_burn_slope.append(generator.fuel_slope * GAL_DIESEL_TO_KWH)
                fuel_burn_intercept.append(generator.fuel_intercept * GAL_DIESEL_TO_KWH)
                fuel_limit.append(generator.fuel_avail * GAL_DIESEL_TO_KWH)
                techs_by_fuel_type.append([tech.upper()])
                fuel_types.append("DIESEL")
            elif tech.lower() == 'boiler':
                fuel_costs = operator.add(fuel_costs, self.boiler_fuel_rate_array)
                # Fuel for boiler is not handled by fuel_burn slope/intercept
                # fuel_burn_slope.append(1 / self.boiler.boiler_efficiency)
                # fuel_burn_intercept.append(0.0)
                fuel_limit.append(self.big_number)
                techs_by_fuel_type.append([tech.upper()])
                fuel_types.append("BOILERFUEL")
            elif tech.lower() == 'chp':
                fuel_costs = operator.add(fuel_costs, self.chp_fuel_rate_array)
                fuel_burn_slope.append(chp.fuel_burn_slope)
                # CHP has a separate fuel burn y-intercept that is size-specific, so assign 0 to this one
                fuel_burn_intercept.append(0.0)
                fuel_limit.append(self.big_number)
                techs_by_fuel_type.append([tech.upper()])
                fuel_types.append("CHPFUEL")
            elif tech.lower() == 'newboiler':
                fuel_costs = operator.add(fuel_costs, self.newboiler_fuel_rate_array)
                # Fuel for newboiler is not handled by fuel_burn slope/intercept
                # fuel_burn_slope.append(1 / self.newboiler.boiler_efficiency)
                # fuel_burn_intercept.append(0.0)
                fuel_limit.append(self.big_number)
                techs_by_fuel_type.append([tech.upper()])
                fuel_types.append("NEWBOILERFUEL")


        return fuel_costs, fuel_limit, fuel_types, techs_by_fuel_type, fuel_burn_slope, fuel_burn_intercept

    def _get_chp_unique_params(self, chp_techs, chp=None):
        """
        In the Julia model we have:
           - d["CHPThermalProdSlope"] = AxisArray(d["CHPThermalProdSlope"],d["CHPTechs"])
           - d["CHPThermalProdIntercept"] = AxisArray(d["CHPThermalProdIntercept"],d["CHPTechs"])
           - d["FuelBurnYIntRate"] = AxisArray(d["FuelBurnYIntRate"],d["CHPTechs"])
           - d["CHPThermalProdFactor"] = vector_to_axisarray(d["CHPThermalProdFactor"],d["CHPTechs"],d[:TimeStep])
        :return: chp_fuel_burn_intercept, chp_thermal_prod_slope, chp_thermal_prod_intercept, chp_derate (all lists)
        """
        # Unique parameters for CHP
        if chp_techs not in [None, []]:
            chp_fuel_burn_intercept = [chp.fuel_burn_intercept]
            chp_thermal_prod_slope = [chp.thermal_prod_slope]
            chp_thermal_prod_intercept = [chp.thermal_prod_intercept]
            chp_derate = [chp.derate]
        else:
            chp_fuel_burn_intercept = list()
            chp_thermal_prod_slope = list()
            chp_thermal_prod_intercept = list()
            chp_derate = list()

        return chp_fuel_burn_intercept, chp_thermal_prod_slope, chp_thermal_prod_intercept, chp_derate
