#!/bin/sh
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

###############################################################################
# This script runs cluster-director-mcp
###############################################################################

export CLUSTER_DIRECTOR_MCP_DEBUG=1

# Update cluster-director-mcp if necessary
echo "----"
echo "Updating cluster-director-mcp..."
(git pull 2>&1 > /dev/null ; make -j  2>&1 > /dev/null) &
git_pull_make_pid=$!

# Clean scratch
echo "----"
echo "Cleaning Scratch space..."
rm -f cluster-director-mcp.scratch/* 2>&1 > /dev/null &

# Check if gcloud is authenticated by trying to print an access token.
# We redirect all output to /dev/null to keep the script's output clean.
echo "Checking if the user is authenticated..."
if gcloud auth print-access-token --quiet &> /dev/null; then
    # If the command succeeds, the user is authenticated.
    ACCOUNT=$(gcloud config get-value account)
    echo "User is authenticated as: $ACCOUNT . Proceeding with script..."
else
    # If the command fails, the user is not authenticated.
    echo "User is not authenticated. Please run 'gcloud auth login' first."
    exit 1
fi

# Check if project is set
echo "----"
echo "Checking if project id is set ..."
PROJECT_ID=$(gcloud config get-value project)
if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: Google Cloud project is not set. Please set a project using 'gcloud config set project YOUR_PROJECT_ID'."
  exit 1
else
  echo "Google Cloud project set to: $PROJECT_ID"
fi

# Check the user has permission to query IAM policy
function check_iam_role_exists() {
  if gcloud projects get-iam-policy "$PROJECT_ID" \
    --flatten="bindings[].members" \
    --format='table(bindings.role, bindings.members)' \
    | grep -qE "$1\s+user\:$USER\@"; then
    echo "Failure: User does not have IAM roles $1"
    echo "Please request $1 from your project admin/owner of $PROJECT_ID"
    exit 1
  else
    echo "Success: User has permissions to query IAM roles."
  fi
}

# Check the user has permission to query IAM policy
echo "----"
echo "Checking if user $USER has permissions to get IAM policies for their project (permission to run: gcloud projects get-iam-policy "$PROJECT_ID") ..."
if gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --format='table(bindings.role, bindings.members)' \
  | grep -qE "does\s+not\s+have\s+permissions\s+" ; then
  echo "Failure: User does not have permissions to query IAM roles."
  echo "Please request the role roles/browser from your project admin/owner of $PROJECT_ID"
  exit 1
else
  echo "Success: User has permissions to query IAM roles."
fi

# Check user has IAM policy compute.osLogin
echo "----"
echo "Checking if user $USER has permissions to ssh into VMs (IAM role: compute.osLogin)..."
check_iam_role_exists "roles\\\/compute.osLogin"

# Check user has permission to impersonate service accounts
echo "----"
echo "Checking if user $USER has permissions to impersonate service accounts (IAM role: iam.serviceAccountUser)..."
check_iam_role_exists "roles\\\/iam.serviceAccountUser"

# Check user has permission to login to VMs
echo "----"
echo "Checking if user $USER has IAM role: roles/compute.instanceAdmin.v1 ..."
check_iam_role_exists "roles\\\/compute.instanceAdmin.v1"

# roles/iap.tunnelResourceAccessor
echo "----"
echo "Checking if user $USER has IAM role: roles/iap.tunnelResourceAccessor ..."
check_iam_role_exists "roles\\\/iap.tunnelResourceAccessor"

# Update gemini settings.json to install MCP servers
scripts/installExtensions.py ~/.gemini/settings.json

# Run cluster-director-mcp
echo "----"
echo -n "Running  based on gemini-cli version "
gemini --version
echo "..."
wait $git_pull_make_pid
if [ -n "$CDMCP_DEBUG" ]; then
    echo "CDMCP_DEBUG is defined."    
    gemini --debug --allowed-mcp-server-names  context7,cluster-director-mcp
else
    gemini --allowed-mcp-server-names  context7,cluster-director-mcp
fi
