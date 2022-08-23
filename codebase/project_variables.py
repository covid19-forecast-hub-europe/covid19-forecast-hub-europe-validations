# -*- coding: utf-8 -*-
"""
Collection of global variables used as inputs to validation functions
  This helps prevent circular imports (between quantile_io and cdc_io)
  and more useful to see all the project-specific parts in one place

@author: kaths
"""
import pandas as pd
import json
import requests 

# Get hub config
config = requests.get('https://raw.githubusercontent.com/epiforecasts/covid19-forecast-hub-europe/main/project-config.json')
project_config = json.loads(config.text)

## covid19.py
FORECAST_WEEK_DAY = project_config['forecast_week_day']
CODES = list(pd.read_csv('https://raw.githubusercontent.com/epiforecasts/covid19-forecast-hub-europe/main/data-locations/locations_eu.csv')['location'])
VALID_TARGET_NAMES = [f"{_} wk ahead {target_variable}" \
                      for _ in range(1, 20) \
                      for target_variable in project_config['target_variables']]
VALID_QUANTILES = project_config['forecast_type']['quantiles']

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


