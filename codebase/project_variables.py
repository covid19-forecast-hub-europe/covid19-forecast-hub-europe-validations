# -*- coding: utf-8 -*-
"""
Collection of global variables used as inputs to validation functions
  This helps prevent circular imports (between quantile_io and cdc_io)
  and more useful to see all the project-specific parts in one place

@author: kaths
"""
import pandas as pd
from pyprojroot import here

## covid19.py
CODES = list(pd.read_csv(here('./data-locations/locations_eu.csv'))['location'])
VALID_TARGET_NAMES = [f"{_} wk ahead inc death" for _ in range(1, 20)] + \
                     [f"{_} wk ahead inc case" for _ in range(1, 20)]
VALID_QUANTILES = [0.010, 0.025, 0.050, 0.100, 0.150, 0.200, 0.250, 0.300,
                   0.350, 0.400, 0.450, 0.500, 0.550, 0.600, 0.650, 0.700,
                   0.750, 0.800, 0.850, 0.900, 0.950, 0.975, 0.990]

## quantile_io.py 
BIN_DISTRIBUTION_CLASS = 'bin'
NAMED_DISTRIBUTION_CLASS = 'named'
POINT_PREDICTION_CLASS = 'point'
SAMPLE_PREDICTION_CLASS = 'sample'
QUANTILE_PREDICTION_CLASS = 'quantile'
OBS_PREDICTION_CLASS = "obs"
REQUIRED_COLUMNS = ('location', 'target', 'type', 'quantile', 'value')
POSSIBLE_COLUMNS = ['location', 'target', 'type', 'quantile', 'value', 'target_end_date', 'forecast_date', 'location_name', 'scenario_id']

## cdc_io
YYYY_MM_DD_DATE_FORMAT = '%Y-%m-%d'  # e.g., '2017-01-17'
CDC_OBSERVED_ROW_TYPE = "Observed"
CDC_POINT_ROW_TYPE = 'Point'
CDC_QUANTILE_ROW_TYPE = "Quantile"
CDC_BIN_ROW_TYPE = 'Bin'
CDC_CSV_HEADER = ['location', 'target', 'type', 'unit', 'bin_start_incl', 'bin_end_notincl', 'value']
SEASON_START_EW_NUMBER = 30


