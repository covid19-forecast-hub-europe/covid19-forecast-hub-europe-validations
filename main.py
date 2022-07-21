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

from codebase.test_formatting import forecast_check, print_output_errors
from codebase.validation_functions.metadata import check_metadata_file
from codebase.validation_functions.non_negative_forecasts import non_negative_values

# Pattern that matches a forecast file added to the data-processed folder.
# Test this regex usiing this link: https://regex101.com/r/wmajJA/1
pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv$")
pat_meta = re.compile(r"^metadata/metadata-.+\.yml$")
pat_other = re.compile(r"^data-processed/(.+)\.csv$")

# Identify if local or Github event
local = os.environ.get('CI') != 'true'
fresh_pr = os.environ.get('GITHUB_EVENT_NAME') in ['pull_request', 'pull_request_target']

# Set up token
if local:
    token = None
    print("Running on LOCAL mode.")
else:
    print("Added token")
    token  = os.environ.get('GH_TOKEN')

if token is None:
    g = Github()
else:
    print(f"Token length: {len(token)}")
    g = Github(token)

# Mount repository
repo_name = os.environ.get('GITHUB_REPOSITORY')
if repo_name is None:
    repo_name = 'epiforecasts/covid19-forecast-hub-europe'
repo = g.get_repo(repo_name)

print(f"Github repository: {repo_name}")

if fresh_pr:
    print(f"Github event name: {os.environ.get('GITHUB_EVENT_NAME')}")
    event = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))

pr = None
comment = ''
files_changed = []

if fresh_pr:
    # Fetch the  PR number from the event json
    pr_num = event['pull_request']['number']
    print(f"PR number: {pr_num}")
    # Use the Github API to fetch the Pullrequest Object. Refer to details here: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html
    # pr is the Pullrequest object
    pr = repo.get_pull(pr_num)
    # fetch all files changed in this PR and add it to the files_changed list.
    files_changed +=[f for f in pr.get_files()]

# if the file is run in local mode,
# and no files are present in the /forecasts folder, ask for a PR number
elif local and not glob.glob("./forecasts/*.csv"):
    # get user input
    pr_num = input("Please enter PR reference number (e.g. 536) : ")
    print(f"PR number: {pr_num}")
    pr = repo.get_pull(int(pr_num))
    files_changed +=[f for f in pr.get_files()]

forecasts = [file for file in files_changed if pat.match(file.filename) is not None]
forecasts_err = [file for file in files_changed if pat_other.match(file.filename) is not None]
metadatas = [file for file in files_changed if pat_meta.match(file.filename) is not None]
other_files = [file for file in files_changed if (pat.match(file.filename) is None and pat_meta.match(file.filename) is None)]

if fresh_pr:
    # IF there are other fields changed in the PR
    if len(other_files) > 0 and len(forecasts) >0 :
        print("PR has other files changed too.")

    if len(metadatas) > 0:
        print("PR has metadata files changed.")

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
        comment += "\n Your submission seem to have deleted some forecasts. Could you provide a reason for the deletion? Thank you!\n\n"

    if changed_forecasts:
        comment += "\n Your submission seem to have updated/renamed some forecasts. Could you provide a reason? Thank you!\n\n"

# Download all forecasts
# create a forecasts directory
os.makedirs('forecasts', exist_ok=True)

# Download all forecasts changed in the PR into the forecasts folder
for f in forecasts:
    if f.status != "removed":
        urllib.request.urlretrieve(f.raw_url, f"./forecasts/{f.filename.split('/')[-1]}")

# Download all metadata files changed in the PR into the forecasts folder
for f in metadatas:
    if f.status != "removed":
        urllib.request.urlretrieve(f.raw_url, f"./forecasts/{f.filename.split('/')[-1]}")

# Run validations on each of these files
errors = {}
warnings = {}

for file in glob.glob("./forecasts/*.csv"):
    error_file = forecast_check(file)
    warning = non_negative_values(file)
    if len(error_file) >0:
        errors[os.path.basename(file)] = error_file

    if len(warning) > 0:
        warnings[os.path.basename(file)] = warning

is_meta_error = False
meta_err_output = {}
for file in glob.glob("./forecasts/*.yml"):
    is_metadata_error, metadata_error_output = check_metadata_file(file)
    if is_metadata_error:
        is_meta_error = True
        meta_err_output[file] = metadata_error_output

# list contains all changes in the data_processed folder
data_processed_changes = forecasts + forecasts_err + metadatas
if data_processed_changes:
    # check if metadata file is present in main repo
    if not metadatas:

        # get all team_model-names in commit (usually only one)
        team_names = []
        for file in data_processed_changes:
            team_names.append(file.filename.split("/")[-2])
        team_names = set(team_names)

        # if the PR doesnt add a metadatafile we have to check if there is a existing file in the main repo
        for name in team_names:
            try:
                repo.get_contents("metadata/metadata-{}.yml".format(name))

            # metadata file doesnt exist and is not added in the PR
            except github.UnknownObjectException:
                is_meta_error = True
                meta_err_output["metadata-{}.yml".format(name)] = ["Missing Metadata"]

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
if comment!='' and not local:
    pr.create_issue_comment(comment)

if is_meta_error or len(errors)>0:
    shutil.rmtree("./forecasts")
    sys.exit("\n ERRORS FOUND EXITING BUILD...")

if len(warnings) > 0:
    warning_message = ""
    for file in warnings.keys():
        warning_message += str(file) + " " + warnings[file] + "\n\n"
    pr.create_issue_comment(warning_message)

# delete checked files from validation
shutil.rmtree("forecasts")
