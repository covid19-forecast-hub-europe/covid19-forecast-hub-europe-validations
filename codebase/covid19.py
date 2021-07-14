from __future__ import absolute_import
# Standard modules
import datetime
from pathlib import Path
import click
import sys

# Local modules
sys.path.append('validation/codebase/')
from .quantile_io import json_io_dict_from_quantile_csv_file

# Use codes, targets, and quantiles
#   as defined in project_variables (ultimately from hub config)
import codebase.project_variables as project

codes = project.CODES
VALID_TARGET_NAMES = project.VALID_TARGET_NAMES
VALID_QUANTILES = project.VALID_QUANTILES
FORECAST_WEEK_DAY = project.FORECAST_WEEK_DAY

#
# validate_quantile_csv_file()
#

def validate_quantile_csv_file(csv_fp):
    """
    A simple wrapper of `json_io_dict_from_quantile_csv_file()` that tosses
    the json_io_dict and just prints validation error_messages.

    :param csv_fp: as passed to `json_io_dict_from_quantile_csv_file()`
    :return: error_messages: a list of strings
    """
    quantile_csv_file = Path(csv_fp)
    click.echo(f"* validating quantile_csv_file '{quantile_csv_file}'...")
    with open(quantile_csv_file) as ecdc_csv_fp:
        # toss json_io_dict:
        target_names = VALID_TARGET_NAMES

        _, error_messages = json_io_dict_from_quantile_csv_file(
                csv_fp = ecdc_csv_fp,
                valid_target_names = target_names,
                codes = codes,
                row_validator = covid19_row_validator,
                addl_req_cols = ['forecast_date', 'target_end_date'])

        if error_messages:
            return error_messages
        else:
            return "no errors"


#
# `json_io_dict_from_quantile_csv_file()` row validator
#

def covid19_row_validator(column_index_dict, row, codes):
    """
    Does COVID19-specific row validation. Notes:
    - Checks in order:
    0. value
    1. location
    2. quantiles
    3. forecast_date and target_end_date (terminates if invalid)
    4. integer in "__ week ahead" (terminates if invalid)
    5. date alignment - week starting Monday ending Sunday

    - Expects these `valid_target_names` passed to
     `json_io_dict_from_quantile_csv_file()`:
         VALID_TARGET_NAMES VALID_SCENARIO_ID

    - Expects these `addl_req_cols` passed to
     `json_io_dict_from_quantile_csv_file()`:
         ['forecast_date', 'target_end_date']
    """

    from .cdc_io import _parse_date  # avoid circular imports

    error_messages = []  # returned value. filled next

    # 0. Validate forecast value - Currently not enforced because truth can contain negative values
    #value = row[column_index_dict['value']]
    #if float(value) < 0:
    #    error_messages.append(f"Error > negative value in forecast: {value!r}. row={row}")

    # 1. validate location (ISO-2 code)
    location = row[column_index_dict['location']]
    if location not in codes:
        error_messages.append(f"Error > invalid ISO-2 location: {location!r}. row={row}")

    row_type = row[column_index_dict['type']]
    if row_type not in ["observed", "point", "quantile"]:
        print(row_type)
        error_messages.append(f"Error > invalid type: {row_type!r}. row={row}")

    # 2. validate quantiles (stored as strings, checked against numeric)
    quantile = row[column_index_dict['quantile']]
    if row[column_index_dict['type']] == 'quantile':
        try:
            if float(quantile) not in VALID_QUANTILES:
                error_messages.append(f"Error > invalid quantile: {quantile!r}. row={row}")
        except ValueError:
            pass  # ignore, caught by `json_io_dict_from_quantile_csv_file()`

    # 3. validate forecast_date and target_end_date
    forecast_date = row[column_index_dict['forecast_date']]
    target_end_date = row[column_index_dict['target_end_date']]

    # 3.1 Expect date formats
    forecast_date = _parse_date(forecast_date)  # None if invalid format
    target_end_date = _parse_date(target_end_date)  # ""
    if not forecast_date or not target_end_date:
        error_messages.append(f"Error > invalid forecast_date or target_end_date format. forecast_date={forecast_date!r}. "
                              f"target_end_date={target_end_date}. row={row}")
        return error_messages

    # 3.2 Expect a minimum 5 days between forecast_date and target_end_date
    date_diff = target_end_date - forecast_date
    if date_diff < datetime.timedelta(days=5):
        error_messages.append(f"Error > target_end_date was <5 days after forecast_date: {target_end_date}. row={row}")
        return error_messages  # terminate - depends on valid target_end_date

    # 4. validate "__ week ahead" increment - must be an int
    target = row[column_index_dict['target']]
    try:
        step_ahead_increment = int(target.split('wk ahead')[0].strip())
    except ValueError:
        error_messages.append(f"Error > non-integer number of weeks ahead in 'wk ahead' target: {target!r}. row={row}")
        return error_messages  # terminate - depends on valid step_ahead_increment

    # 5. Validate date alignment (Sunday-Saturday epi week)
    weekday_to_sun_based = {i: i + 2 if i != 6 else 1 for i in range(7)}  # Sun=1, Mon=2, ..., Sat=7

    # 5.1 for x week ahead targets, weekday(target_end_date) should be a Sat
    if weekday_to_sun_based[target_end_date.weekday()] != 7:
       error_messages.append(f"Error > target_end_date was not a Saturday: {target_end_date}. row={row}")
       return error_messages  # terminate - depends on valid target_end_date

    # 5.2 Forecast date should always be Mon -- no longer checked

    # 5.3 Set expected target end date from forecast date
    # - Set which weekdays are can start within the forecast epiweek
    #   i.e. Sunday and Monday
    #   TODO: use our config file to get this and translate into epi-weekdays
    overlap_days = 1, 2
    # - Get weekday of forecast date
    forecast_weekday = weekday_to_sun_based[forecast_date.weekday()]
    # - Rebase forecast date to a Saturday
      # - For allowed weekdays within epiweek, rebase to last day of prev epiweek
    sat_forecast_date = forecast_date - datetime.timedelta(forecast_weekday)
      # - For all other weekdays, rebase to the next epiweek (after forecast date)
    if forecast_weekday not in overlap_days:
        sat_forecast_date = sat_forecast_date + datetime.timedelta(7)
    # - Go forward in weeks to set a target end date based on "n wk ahead"
    exp_target_end_date = sat_forecast_date + datetime.timedelta(weeks = step_ahead_increment)
    # - Validate
    if target_end_date != exp_target_end_date:
        error_messages.append(f"Error > target_end_date was not the expected Saturday. forecast_date = {forecast_date}, "
                                  f"target_end_date={target_end_date}. Expected target end date = {exp_target_end_date}, "
                                  f"row={row}")

    # done!
    return error_messages





# forecast_date = 2021-07-09,
# target_end_date=2021-07-17.
# Expected target end date = 2021-07-18
