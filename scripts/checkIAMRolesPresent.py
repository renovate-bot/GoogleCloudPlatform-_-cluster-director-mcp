#!/usr/bin/env python3

import json
import subprocess

#============================================================
#  This script verifies the user has the requisite IAM roles
#============================================================

def check_user_role(json_str, target_user, target_role):
    """
    Parses a flattened IAM JSON file and checks for a specific user/role pair.
    """
    try:
        iam_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error: Parse error with JSON {json_str}")
        print(f"Error Message: {e.msg}")
        print(f"Line Number:   {e.lineno}")
        print(f"Column Number: {e.colno}")
        print(f"Char Index:    {e.pos}")        
        return False
    
    found = False
    
    data = iam_data
    if 'bindings' in iam_data:
        data = iam_data['bindings']

    for entry in data:
        role = entry.get('role', '')
        if role == target_role:
            members = entry.get('members', '')
            for member in members:
                if target_user in member:
                    found = True
                    break 
        
    if not found:
        print("No match for user: " + target_user + " in role: " + target_role)
    
    return found

def get_shell_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Check if it succeeded
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        print("Error running cmd: " + " ".join(cmd))
        print("Error message: " + result.stderr)
        exit(1)

# --- Execution ---
if __name__ == "__main__":

    # The command you want to run (as a list of strings)
    account_cmd = ["gcloud", "config", "get-value", "account"]
    account = get_shell_cmd(account_cmd)

    project_cmd = ["gcloud", "config", "get", "project"]
    project = get_shell_cmd(project_cmd)

    iam_cmd = ["gcloud", 
               "projects", 
               "get-iam-policy", 
                project,
                "--format=json"]
    iam_json_str = get_shell_cmd(iam_cmd)

    # owner is a basic role and includes all other roles
    if check_user_role(iam_json_str, account, "roles/owner"):
        print("SUCCESS: User has IAM role roles/owner")
        exit(0)

    # editor is a basic role and includes all other roles
    if check_user_role(iam_json_str, account, "roles/editor"):
        print("SUCCESS: User has IAM role roles/editor")
        exit(0)

    # Verify roles
    iam_roles = ["roles/hypercomputecluster.editor", 
                 "roles/compute.osLogin", 
                 "roles/iam.serviceAccountUser", 
                 "roles/compute.instanceAdmin.v1",
                 "roles/iap.tunnelResourceAccessor"]
    
    missingIamRoles = False
    for iam_role in iam_roles:
        if check_user_role(iam_json_str, account, iam_role):
            print("SUCCESS: User has IAM role " + iam_role)
        else:
            missingIamRoles = True
            print("ERROR: User does NOT have IAM role " + iam_role)

    if missingIamRoles:
        exit(1)
    else:
        exit(0)
