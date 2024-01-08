from urllib.parse import urlparse

import requests
import base64
import json

# put your GitHub API Token here, rate limit = 5000 req/h
access_token = ""


def get_commit_details(repo_url, commit_sha):
    api_url = f"https://api.github.com/repos/{repo_url}/commits/{commit_sha}"
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        commit_data = response.json()
        return commit_data
    else:
        print(f"Failed to fetch commit details. Status code: {response.status_code}")
        print(response.reason)
        return None


def get_file_content(repo_url, commit_sha, file_path):
    api_url = f"https://api.github.com/repos/{repo_url}/contents/{file_path}?ref={commit_sha}"
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        file_data = response.json()
        return file_data.get('content', None)
    elif response.status_code == 404:  # file is not found
        return None
    else:
        print(f"Failed to fetch file content. Status code: {response.status_code}")
        return None


def extract_pre_commit_code(owner, repo, commit_sha, output_file_path):
    repo_url = f"{owner}/{repo}"
    commit_details = get_commit_details(repo_url, commit_sha)

    if commit_details is not None:
        parent_commit_sha = commit_details['parents'][0]['sha']  # TODO: assumes a single parent for simplicity

        current_commit_files = commit_details['files']

        with open(output_file_path, 'ab') as output_file:
            for file_change in current_commit_files:
                file_path = file_change['filename']
                if not file_path.endswith('.java'):
                    continue  # we only want to make predictions for Java files

                parent_content_base64 = get_file_content(repo_url, parent_commit_sha, file_path)

                if parent_content_base64 is not None:
                    parent_content = base64.b64decode(parent_content_base64).decode('utf-8', errors='replace')

                    output_file.write(f"\n\nFile: {file_path}\n".encode('utf-8'))
                    output_file.write(parent_content.encode('utf-8'))
                else:
                    pass
                    # print(f"Skipping file {file_path}: file not present in parent commit.")

            print(f"Wrote file: {output_file.name}")


if __name__ == "__main__":
    with open('refactorings.json') as json_file:
        refactorings_data = json.load(json_file)

    for entry in refactorings_data:
        repo_url = entry['repository']
        parsed_url = urlparse(repo_url)
        owner, repo = parsed_url.path.lstrip('/').split('/', 1)
        repo = repo.rstrip('.git')
        commit_sha = entry['sha1']
        output_file_path = f"data/{owner}_{repo}_{commit_sha}.md"

        # annotate the commit with refactoring types, these will server as the labels
        with open(output_file_path, 'ab') as output_file:
            for refactoring in entry.get('refactorings', []):
                refactoring_type = refactoring['type']
                refactoring_type_str = f"\nRefactoring Type: {refactoring_type}\n"
                output_file.write(refactoring_type_str.encode('utf-8'))

        extract_pre_commit_code(owner, repo, commit_sha, output_file_path)




