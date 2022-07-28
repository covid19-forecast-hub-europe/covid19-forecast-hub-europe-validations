from __future__ import absolute_import

from zoltpy import util
from zoltpy.connection import ZoltarConnection
import os
import sys

import glob
from pathlib import Path
import pprint
import yaml
import json
import hashlib
import json

if (os.environ.get('Z_USERNAME') == None):
    print("Run within hub submodule, and/or set Zoltar access as environment variables.")
    raise SystemExit

sys.path.append('validation/')

from codebase.quantile_io import json_io_dict_from_quantile_csv_file
from codebase.covid19 import VALID_TARGET_NAMES, covid19_row_validator, validate_quantile_csv_file
from codebase.project_variables import REQUIRED_COLUMNS, CODES

cwd_p = Path(__file__).parent.resolve()
all_forecasts = glob.glob('./data-processed/**/*-*.csv')
pprint.pprint(all_forecasts)

# meta info
with open('project-config.json') as f:
    hub_config = json.load(f)
project_name = 'ECDC European COVID-19 Forecast Hub'
project_obj = None
conn = util.authenticate()
repo_url = hub_config['repo_url'] + '/tree/main/data-processed'

project_obj = [project for project in conn.projects if project.name == project_name][0]
project_timezeros = [timezero.timezero_date for timezero in project_obj.timezeros]
models = [model for model in project_obj.models]
model_abbrs = [model.abbreviation for model in models]
zoltar_forecasts = []
repo_forecasts = []


def read_validation_db():
    try:
        with open('validation/zoltar_scripts/validated_file_db.json', 'rb') as f:
            l = json.load(f)
    except Exception as ex:
        l = {}
    return dict(l)


def write_db(db):
    with open('validation/zoltar_scripts/validated_file_db.json', 'w') as fw:
        json.dump(db, fw, indent=4)

# Function to read metadata file to get model name
def metadata_dict_for_file(metadata_file):
    with open(metadata_file, encoding="utf8") as metadata_fp:
        metadata_dict = yaml.safe_load(metadata_fp)
    return metadata_dict

def get_forecast_info(name):
    print(name)
    path = list(filter(lambda f: name in f, all_forecasts))[0]
    # abbr = name.split('.')[0].split('-')[-1]
    return path


def config_from_metadata(metadata):
    model_config = {}
    model_config['name'] = metadata['model_name']
    model_config['abbreviation'] = metadata['model_abbr']
    model_config['team_name'] = metadata['team_name']
    model_config['description'] = metadata['methods']
    model_config['methods'] = metadata['methods_long'] if metadata.get('methods_long') != None else 'NA'
    model_config['license'] = metadata['license']
    model_config['contributors'] = metadata['model_contributors']
    model_config['citation'] = metadata['citation'] if metadata.get('citation') != None else 'NA'
    model_config['notes'] = metadata['team_model_designation']
    model_config['home_url'] = metadata['website_url'] if metadata.get('website_url') != None else url + dir_name
    model_config['aux_data_url'] = 'NA'
    return model_config


def create_model(file_path, metadata):
    model_config = config_from_metadata(metadata)
    try:
        print('Creating model with config: ')
        pprint.pprint(model_config)
        models.append(project_obj.create_model(model_config))
    except Exception as ex:
        raise ex
        return ex

def create_timezero(tz):
    try:
        project_obj.create_timezero(tz)
        project_timezeros.append(tz)
    except Exception as ex:
        return ex

def extract_model_name(forecast_name):
    return forecast_name.split('-', maxsplit = 3)[3].split('.')[0]

def upload_forecast(forecast_name):
    path = get_forecast_info(forecast_name)
    model_name = extract_model_name(forecast_name)
    db = read_validation_db()

    metadata = metadata_dict_for_file('model-metadata/{}.yml'.format(model_name))
    if f"{metadata['model_abbr']}"  not in [m.abbreviation for m in models]:
        create_model(path, metadata)

    time_zero_date = '-'.join(forecast_name.split('-')[:3])

    if time_zero_date not in [timezero.timezero_date for timezero in project_obj.timezeros]:
        create_timezero(time_zero_date)

    # print(forecast_name, metadata, time_zero_date)
    if path is not None:
        errors_from_validation = validate_quantile_csv_file(path)
        if errors_from_validation != "no errors":
            print(errors_from_validation)
            return errors_from_validation, True
        with open(path) as fp:
            print('uploading %s' % path)
            checksum = hashlib.md5(str(fp.read()).encode('utf-8')).hexdigest()
            fp.seek(0)
            quantile_json, error_from_transformation = json_io_dict_from_quantile_csv_file(fp,
            VALID_TARGET_NAMES,
            CODES,
            covid19_row_validator,
            REQUIRED_COLUMNS)

            if len(error_from_transformation) > 0:
                return error_from_transformation, True

            try:
                fr = util.upload_forecast(conn, quantile_json, path, project_name, f"{metadata['model_abbr']}" , time_zero_date)
                db[forecast_name] = checksum
                write_db(db)
                return None, fr
            except Exception as e:
                raise e
                return e, True
    pass

if __name__ == '__main__':
    for model in models:
        existing_forecasts = [forecast.source for forecast in model.forecasts]
        zoltar_forecasts.extend(existing_forecasts)
    for directory in [model for model in os.listdir('./data-processed/') if "." not in model]:
        forecasts = [forecast for forecast in os.listdir('./data-processed/'+directory+"/") if ".csv" in forecast]
        repo_forecasts.extend(forecasts)
    print("number of forecasts in zoltar: " + str(len(zoltar_forecasts)))
    print("number of forecasts in repo: " + str(len(repo_forecasts)))
    print()
    print('----------------------------------------------------------')
    print()
    forecasts_to_upload = []
    for forecast in repo_forecasts:
        if forecast not in zoltar_forecasts:
            print("This forecast in repo but not in zoltar "+forecast)
            forecasts_to_upload.append(forecast)

    l = list(map(upload_forecast, forecasts_to_upload))
    print(l)
    print('Forecasts to upload: ')
    pprint.pprint(forecasts_to_upload)
