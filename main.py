# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 19:04:35 2021

@author: Jannik
"""

import re
import os
import json
import glob
from github import Github
import github
import urllib.request
import sys
import shutil

from codebase.test_formatting import forecast_check
from codebase.test_formatting import forecast_check, validate_forecast_file, print_output_errors
from codebase.validation_functions.metadata import check_for_metadata, get_metadata_model, output_duplicate_models
from codebase.validation_functions.non_negative_forecasts import non_negative_values
from codebase.validation_functions.integer_forecasts import integer_values

# Pattern that matches a forecast file added to the data-processed folder.
# Test this regex usiing this link: https://regex101.com/r/wmajJA/1
pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$")
pat_meta = re.compile(r"^data-processed/(.+)/metadata-\1\.txt$")
pat_other = re.compile(r"^data-processed/(.+)\.csv$")

local = os.environ.get('CI') != 'true'
# local = True
if local:
    token = None
    print("Running on LOCAL mode. Checking files in forecasts/")
else:
    print("Added token")
    token  = os.environ.get('GH_TOKEN')
    print(f"Token length: {len(token)}")

if token is None:
    g = Github()
else:
    g = Github(token)

# mount repository
repo_name = os.environ.get('GITHUB_REPOSITORY')
if repo_name is None:
    repo_name = 'epiforecasts/covid19-forecast-hub-europe'
repo = g.get_repo(repo_name)

if not local:
    print(f"Github repository: {repo_name}")
    print(f"Github event name: {os.environ.get('GITHUB_EVENT_NAME')}")
    event = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))

pr = None
comment = ''
files_changed = []

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
    # Fetch the  PR number from the event json
    pr_num = event['pull_request']['number']
    print(f"PR number: {pr_num}")

    # Use the Github API to fetch the Pullrequest Object. Refer to details here: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html
    # pr is the Pullrequest object
    pr = repo.get_pull(pr_num)

    # fetch all files changed in this PR and add it to the files_changed list.
    files_changed +=[f for f in pr.get_files()]

# if the file is run in local mode and no files are present in the /forecasts folder
elif local and not glob.glob("./forecasts/*.csv"):
    # get user input
    pr_num = input("Please enter PR reference number:")
    print(f"PR number: {pr_num}")

    # Use the Github API to fetch the Pullrequest Object. Refer to details here: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html
    # pr is the Pullrequest object
    pr = repo.get_pull(int(pr_num))

    # fetch all files changed in this PR and add it to the files_changed list.
    files_changed +=[f for f in pr.get_files()]

forecasts = [file for file in files_changed if pat.match(file.filename) is not None]
forecasts_err = [file for file in files_changed if pat_other.match(file.filename) is not None]
metadatas = [file for file in files_changed if pat_meta.match(file.filename) is not None]
other_files = [file for file in files_changed if (pat.match(file.filename) is None and pat_meta.match(file.filename) is None)]

if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
    # IF there are other fields changed in the PR
    #TODO: If there are other files changed as well as forecast files added, then add a comment saying so.
    if len(other_files) > 0 and len(forecasts) >0:
        print(f"PR has other files changed too.")
        if pr is not None:
            pr.add_to_labels('other-files-updated')

    if len(metadatas) > 0:
        print(f"PR has metadata files changed.")
        if pr is not None:
            pr.add_to_labels('metadata-change')

    if len(forecasts) > 0:
        if pr is not None:
            pr.add_to_labels('data-submission')

    deleted_forecasts = False
    changed_forecasts = False

    # `f` is an object of type: https://pygithub.readthedocs.io/en/latest/github_objects/File.html
    # `forecasts` is a list of `File`s that are changed in the PR.
    for f in forecasts:
        # check if file is remove
        if f.status == "removed":
            deleted_forecasts = True

        # if file status is not "added" it is probably "renamed" or "changed"
        elif f.status != "added":
            changed_forecasts = True

    if deleted_forecasts:
        pr.add_to_labels('forecast-deleted')
        comment += "\n Your submission seem to have deleted some forecasts. Could you provide a reason for the deletion? Thank you!\n\n"

    if changed_forecasts:
        pr.add_to_labels('forecast-updated')
        comment += "\n Your submission seem to have updated/renamed some forecasts. Could you provide a reason? Thank you!\n\n"

# Download all forecasts
# create a forecasts directory
# os.makedirs('forecasts', exist_ok=True)

# Download all forecasts changed in the PR into the forecasts folder
for f in forecasts:
    if f.status != "removed":
        urllib.request.urlretrieve(f.raw_url, f"./forecasts/{f.filename.split('/')[-1]}")

# Download all metadat files changed in the PR into the forecasts folder
for f in metadatas:
    if f.status != "removed":
        urllib.request.urlretrieve(f.raw_url, f"./forecasts/{f.filename.split('/')[-1]}")

# Run validations on each of these files
errors = {}
warnings = {}

for file in glob.glob("./forecasts/*.csv"):
    error_file = forecast_check(file)
    warning = non_negative_values(file)
    warning = integer_values(file, warning)
    if len(error_file) >0:
        errors[os.path.basename(file)] = error_file

    if len(warning) > 0:
        warnings[os.path.basename(file)] = warning[0]

FILEPATH_META = "./forecasts/"
is_meta_error, meta_err_output = check_for_metadata(filepath=FILEPATH_META)

# list contains all changes in the data_processed folder
data_processed_changes = forecasts + forecasts_err + metadatas
if data_processed_changes:
    # check if metadata file is present in main repo
    if not metadatas:

        # get all team_model-names in commit (usually only one)
        team_names = []
        for file in data_processed_changes:
            team_names.append(file.contents_url.split("/")[-2])
        team_names = set(team_names)

        # if the PR doesnt add a metadatafile we have to check if there is a existing file in the main repo
        for name in team_names:
            try:
                repo.get_contents("data-processed/{}/metadata-{}.txt".format(name, name))

            # metadata file doesnt exist and is not added in the PR
            except github.UnknownObjectException:
                is_meta_error = True
                meta_err_output["{}/metadata-{}.txt".format(name, name)] = ["Missing Metadata"]

# look for .csv files that dont match pat regex
for file in other_files:
    if file.filename[:14] == "data-processed" and ".csv" in file.filename:
        #print(file.filename)
        err_message = "File does not match forecast file naming convention: <date>-<team>-<model>.csv"
        errors[file.filename] = [err_message]

if len(errors) > 0:
    comment+="\n\n Your submission has some validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
print_output_errors(errors, prefix='data')

if is_meta_error:
    comment+="\n\n Your submission has some metadata validation errors. Please check the logs of the build under the \"Checks\" tab to get more details about the error. "
print_output_errors(meta_err_output, prefix="metadata")

# add the consolidated comment to the PR
if comment!='' and not 'local':
    pr.create_issue_comment(comment)

if is_meta_error or len(errors)>0:
    shutil.rmtree("./forecasts")
    sys.exit("\n ERRORS FOUND EXITING BUILD...")

forecasts_to_vis = False

if len(warnings) > 0:
    warning_message = ""
    for file in warnings.keys():
        warning_message += str(file) + " " + warnings[file] + "\n\n"
    pr.create_issue_comment(warning_message)

# add visualization of forecasts
if not local:
    if forecasts:
        comment += "Preview of submitted forecast:\n\n"
        for f in forecasts:
            if f.status != "removed":
                forecasts_to_vis = True
                vis_link = "https://epiforecasts.shinyapps.io/ecdc_submission/?file=" + f.raw_url
                comment += vis_link + "\n\n"

        if forecasts_to_vis:
            pr.create_issue_comment(comment)

# delete checked files from validation
files = glob.glob("./forecasts/*.*")
for file in files:
    os.remove(file)
