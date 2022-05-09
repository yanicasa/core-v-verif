# Copyright 2022 Thales DIS design services SAS
#
# Licensed under the Solderpad Hardware Licence, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.0
# You may obtain a copy of the License at https://solderpad.org/licenses/
#
# Original Author: Yannick Casamatta (yannick.casamatta@thalesgroup.com)
from yaml import safe_load
import os
import re
import pprint
import yaml
import datetime
import sys
import subprocess

# arguments: inputdir outputfile

cwd = os.getcwd()

dashboard_url = os.environ['DASHBOARD_URL']
git_email = os.environ['DASHBOARD_USER_EMAIL']
git_name = os.environ['DASHBOARD_USER_NAME']

pipeline_creation_timestamp = int(datetime.datetime.strptime(os.environ['CI_PIPELINE_CREATED_AT'], '%Y-%m-%dT%H:%M:%S%z').timestamp())
pipeline_end_timestamp = int(datetime.datetime.now().timestamp())
pipeline_duration = pipeline_end_timestamp - pipeline_creation_timestamp

try:
    workflow_type = os.environ['WORKFLOW_TYPE']
except KeyError:
    workflow_type = "gitlab"

workflow_action = os.environ['WORKFLOW_EVENT']

if workflow_type == 'github':  # (from wrapper)
    
    workflow_uid = os.environ['WORKFLOW_RUN_ID']
    workflow_repo_owner = os.environ['WORKFLOW_REPO_OWNER']
    workflow_repo = os.environ['WORKFLOW_REPO']  # cvv or cva6
    workflow_commit_subject = os.environ['WORKFLOW_COMMIT_MESSAGE']
    workflow_commit_author = os.environ['WORKFLOW_COMMIT_AUTHOR']
    cvv_branch = os.environ['CORE_V_VERIF_BRANCH']
    cvv_sha = os.environ['CORE_V_VERIF_HASH']
    cva6_branch = os.environ['CVA6_BRANCH']
    cva6_sha = os.environ['CVA6_HASH']
else:  # gitlab (from core-v-verif or cva6 repositories)
    workflow_uid = os.environ['CI_PIPELINE_ID']
    if os.environ['SCOPE_CVV'] == 'true':
        workflow_repo = 'core-v-verif'
        cvv_branch = os.environ['CI_COMMIT_REF_NAME']
        cvv_sha = os.environ['CI_COMMIT_SHA']
        cva6_branch = os.environ['CVA6_BRANCH']
        cva6_sha = os.environ['CVA6_HASH']
    else:
        workflow_repo = 'cva6'
        cvv_branch = os.environ['CORE_V_VERIF_BRANCH']
        cvv_sha = os.environ['CORE_V_VERIF_HASH']
        cva6_branch = os.environ['CI_COMMIT_REF_NAME']
        cva6_sha = os.environ['CI_COMMIT_SHA']
    workflow_commit_subject = os.environ['CI_COMMIT_MESSAGE']
    workflow_commit_author = os.environ['CI_COMMIT_AUTHOR']

if len(workflow_commit_subject) > 60:
    title = workflow_commit_subject[0:60] + '...'
else :
    title = workflow_commit_subject
# limit injection through commit message, could be improved!
title = re.sub('[<>\n]*', '', title)

if workflow_repo == "cva6":
    workflow_commit_ref_name = cva6_branch
    workflow_commit_sha = cva6_sha
else:  # workflow_repo == "cvv":
    workflow_commit_ref_name = cvv_branch
    workflow_commit_sha = cvv_sha


pipeline = {
    'token': 'YC' + str(pipeline_creation_timestamp).replace('.', ''),
    'timestamp': pipeline_creation_timestamp,
    'runtime': pipeline_duration,
    'workflow_action': workflow_action,
    'workflow_uid': workflow_uid,
    'workflow_repo': workflow_repo,
    'title': title,
    'description': "",
    'ref_name': workflow_commit_ref_name,
    'author': workflow_commit_author,
    'sha': workflow_commit_sha,
    'env': {
        'cva6': {
            'sha': cva6_sha,
            'branch': cva6_branch
        },
        'core-v-verif': {
            'sha': cvv_sha,
            'branch': cvv_branch
        }
    },
    'status': "pass",  # overridden when jobs are loaded
    'label': "PASS",  # overridden when jobs are loaded
    'jobs': []
}

dir_list = os.listdir(sys.argv[1])
for f in dir_list:
    with open(sys.argv[1] + "/" + f, 'r') as job_report:
        report = safe_load(job_report)
        pipeline["jobs"].append(report)
        if report['status'] != 'pass':
            pipeline["status"] = 'fail'
            pipeline["label"] = 'FAIL'

pprint.pprint(pipeline)

filename = re.sub('[^\w\.]', '', sys.argv[2])
print(filename)

with open(f'{sys.argv[1]}/{filename}', 'w+') as f:
    yaml.dump(pipeline, f)



try:
  print(subprocess.check_output(f'''
echo "git clone {dashboard_url} .gitlab-ci/dashboard_tmp"
git clone {dashboard_url} .gitlab-ci/dashboard_tmp
mkdir -p .gitlab-ci/dashboard_tmp/pipelines_{workflow_repo}
ls -al {sys.argv[1]}
cp {sys.argv[1]}/{filename} .gitlab-ci/dashboard_tmp/pipelines_{workflow_repo}/
ls -al .gitlab-ci/dashboard_tmp/pipelines_{workflow_repo}
cd .gitlab-ci/dashboard_tmp
pwd
git status
git config user.email {git_email}
git config user.name {git_name}
echo "git add pipelines_{workflow_repo}/{filename}"
git add pipelines_{workflow_repo}/{filename}
git status
echo "{workflow_repo}: {title}" 
echo git commit -m  "{workflow_repo}: {title}" 
git commit -m  "{workflow_repo}: {title}"|| echo nok && echo fail
git log
echo 2
git push
echo 3
cd -
''', shell=True))
except subprocess.CalledProcessError as e:
    print(f"Error: {e.output}")
