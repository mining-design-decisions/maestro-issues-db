import requests  # To get the data
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.auth import HTTPBasicAuth
from jira import JIRA
from multiprocessing import Pool
import config

from pymongo import MongoClient  # Database to store the data
import json  # File IO
from time import time  # To time the duration of the requests
from time import sleep
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


MONGO_URL = 'mongodb://localhost:27017'
INVALID_JIRAS = ['Mindville', 'MariaDB']
with open('../0. DataDefinition/jira_data_sources.json') as f:
    jira_data_sources = json.load(f)
# Apache projects requiring authentication
APACHE_AUTH_PROJECTS = [
    'DATALAB',
    'CLOUDSTACK',
    'COUCHDB',
    'DAYTRADER',
    'DELTASPIKE',
    'GERONIMO',
    'GSHELL',
    'INFRA',
    'MYNEWT',
    'RIVER',
    'SANTUARIO',
    'SOLR',
    'XALANJ',
    'YOKO'
]


def check_jira_url(jira_url):
    print('')
    print(f"💡 Check Jira: {jira_url}")
    print('')
    # CHECK PROVIDED JIRA URL AVAILABILITY
    print(f'Checking Jira url existence with GET: {jira_url}')
    try:
        requests.head(jira_url)
    except ConnectionError:
        print('❌ Provided Jira base url does not exist')
        return
    else:
        print('✅ Provided Jira base url is reachable')

    # CHECK PROVIDED JIRA URL API AVAILABILITY
    response = requests.get(jira_url + '/rest/api/2/issuetype')
    print('')
    print(f'Checking Jira api with GET: {response.url}')
    # Check response code
    if response.status_code < 300:
        print('✅ Jira API returned a successful response')
    else:
        print(response.status_code)
        print(response.text)
        print(response.url)
        print('❌ Jira API did not return a successful response')
        return

    # CHECK NUMBER OF ISSUES
    response = requests.get(jira_url + '/rest/api/2/search?jql=&maxResults=0')
    print('')
    print(f"Retrieving total issue count with GET: {response.url}")
    # Check response code
    if response.status_code < 300:
        print(f"Total Number of Issues: {response.json()['total']}")
        print('✅ Jira API returned a successful response')
    else:
        print(response.status_code)
        print(response.text)
        print(response.url)
        print('❌ Jira API did not return a successful response')
        return


def check_jira_urls():
    # Check all Jira URLs in provided jira_data_sources
    for jira_name, jira_obj in jira_data_sources.items():

        # Ignore Jiras that we know are now unreachable or empty
        if jira_name in INVALID_JIRAS:
            continue

        check_jira_url(jira_obj['jira_url'])


def format_duration(start_time, end_time):
    # Get the total seconds of the duration
    seconds = end_time - start_time
    # Calculate the other time
    milliseconds = int((seconds % 1) * 10000)
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    # Trim the values to fit in their appopriate slots
    display_minutes = int(minutes % 60)
    display_seconds = int(seconds % 60)

    return f"{hours:02}:{display_minutes:02}:{display_seconds:02}.{milliseconds:04}"


def download_issue_type_info():
    # Write the result to a JSON
    output_json = {}

    for jira_name, jira_data in jira_data_sources.items():

        # Ignore Jiras that we know are now unreachable or empty
        if jira_name in INVALID_JIRAS:
            continue

        # Build the URL to get the information from
        jira_issuetype_url = jira_data['jira_url'] + '/rest/api/2/issuetype'

        # Get the issuetype definitions
        documented_issuetypes = {
            issuetype['name']: issuetype
            for issuetype in requests.get(jira_issuetype_url).json()
        }

        # Save the information
        output_json[jira_name] = documented_issuetypes

    # Write JSON to file
    with open('jira_issuetype_information.json', 'w', encoding='utf-8') as json_file:
        json.dump(output_json, json_file, ensure_ascii=False, indent=4)


def download_issuelink_type_info():
    # Write the result to a JSON
    output_json = {}

    for jira_name, jira_data in jira_data_sources.items():

        # Ignore Jiras that we know are now unreachable or empty
        if jira_name in INVALID_JIRAS:
            continue

        # Build the URL to get the information from
        jira_issuelinktype_url = jira_data['jira_url'] + '/rest/api/2/issueLinkType'

        # Get the issuelinktype definitions
        documented_issuelinktypes = {
            issuelinktype['name']: issuelinktype
            for issuelinktype in requests.get(jira_issuelinktype_url).json()['issueLinkTypes']
        }

        # Save the information
        output_json[jira_name] = documented_issuelinktypes

    # Write JSON to file
    with open('jira_issuelinktype_information.json', 'w', encoding='utf-8') as json_file:
        json.dump(output_json, json_file, ensure_ascii=False, indent=4)


def download_issue_field_info():
    jiras_fields_information = {}

    for jira_name, jira_data in jira_data_sources.items():

        # Ignore Jiras that we know are now unreachable or empty
        if jira_name in INVALID_JIRAS:
            continue

        # Query Jira for field information
        response = requests.get(f"{jira_data['jira_url']}/rest/api/2/field")
        # Store result in JSON
        jiras_fields_information[jira_name] = response.json()

    # Write JSON to file for later use
    with open('jira_field_information.json', 'w', encoding='utf-8') as json_file:
        json.dump(jiras_fields_information, json_file, ensure_ascii=False, indent=4)


def get_jira_server(jira_data_source, disable_auth=False):
    server = jira_data_source['jira_url']
    if disable_auth or jira_data_source['name'] != 'Apache':
        return JIRA(server)
    return JIRA(server, basic_auth=(config.username, config.password))


def get_response(jira, start_index, iteration_max=100):
    return jira.search_issues(
        f'updated<="2023-03-07 16:00"  order by created asc',
        startAt={start_index},
        maxResults={iteration_max},
        expand='changelog',
        json_result=True)


def download_and_write_data_mongo(
        jira_data_source,
        num_desired_results=None,  # Leave as "None" to download all, otherwise specify a number
        iteration_max=250,  # Recommended to keep at or below 500
        start_index=0,  # This allows you to start back up from a different place
        num_available_results=None
):
    db = MongoClient(MONGO_URL)['JiraRepos']
    jira = get_jira_server(jira_data_source)

    collection = db[jira_data_source['name']]

    # iteration_max is the number of issues the script will attempt to get at one time.
    # The Jira default max is 1000. Trying with 1000 consistently returned errors after a short while
    # as the object being returned was likely too large. Values of 500 or less serve no particular issue
    # to the script except that more calls (of smaller size) have to be made.

    # How many issues to collect before writing to MongoDB
    num_issues_per_write = 10000

    last_write_start_index = start_index
    issues = []

    if num_available_results is None:
        # Available and requested number of results
        num_available_results = get_response(jira, 0, 0)['total']
        print(f'Number of Desired Results   : {num_desired_results if num_desired_results else "All"}')
        print(f'Number of Available Results : {num_available_results}')
        print('')

    # Set the number of results to retrieve based on information from Jira server
    if not num_desired_results:
        num_remaining_results = num_available_results
    else:
        num_remaining_results = min(int(num_desired_results), num_available_results)
    # Adjust remaining results based on their start index
    num_remaining_results -= start_index

    # Collect results while there are more results to gather
    issues_downloaded = 0
    max_count_width = len(str(num_remaining_results)) + 1
    print(f"Total Remaining:{num_remaining_results:< {max_count_width}}")
    while num_remaining_results > 0:

        # Start a timer for this particular chunk
        start_time = time()

        # Number of items to retrieve
        num_items_to_retrieve = min(iteration_max, num_remaining_results)

        # Get issues from Jira
        response_json = get_response(jira, start_index, num_items_to_retrieve)
        if 'issues' in response_json:
            # Add issues to program list
            issues.extend(response_json['issues'])
            num_returned_issues = len(response_json['issues'])

        # Adjust the remaining results to get
        num_remaining_results -= num_returned_issues

        # Print progress for user
        end_index = start_index + num_returned_issues - 1
        print(
            f"Total Remaining:{num_remaining_results:< {max_count_width}}  "
            f"Retrieved Items: {start_index:< {max_count_width}} - {end_index:< {max_count_width}}  "
            f"Duration: {format_duration(start_time, time())}")

        # Move the start index
        start_index += num_returned_issues

        # Write the issues to file IF there are enough of them. This is a nice way to save state and start over at a
        # certain place if there are too many to download in one go.
        if len(issues) >= num_issues_per_write or num_remaining_results == 0 or num_returned_issues == 0:
            # Delete existing issues before updating
            ids = [issue['id'] for issue in issues]
            collection.delete_many({'id': {'$in': ids}})

            # Write the data to mongodb
            collection.insert_many(issues)

            print('... Issues written to database ...')
            last_write_start_index = start_index

            issues_downloaded += len(issues)
            issues = []  # Clear the issues so that our memory doesn't get too full

        # If we have for some reason run out of results, we may want to react to this in some way
        if num_returned_issues == 0:
            print('Number of Returned Issues is 0. This is strange and should not happen. Investigate.')
            return

    print('')
    print(f"Number of Downloaded Issues: {issues_downloaded}")


def download_multiprocessed(jira_name, jira_data_source, start_index=0):
    # Available and requested number of results
    jira = get_jira_server(jira_data_sources[jira_name])
    num_available_results = get_response(jira, 0, 0)['total']
    args = []
    batch_size = 1000
    while start_index + batch_size <= num_available_results:
        args.append([jira_data_source,
                     start_index + batch_size,
                     batch_size,
                     start_index,
                     num_available_results])
        start_index += batch_size
    args.append([
        jira_data_source,
        num_available_results,
        batch_size,
        start_index,
        num_available_results
    ])

    pool = Pool(10)
    pool.starmap(download_and_write_data_mongo, args)
    pool.close()
    pool.join()


def get_auth_projects():
    jira_auth = get_jira_server(jira_data_sources['Apache'])
    jira_non_auth = get_jira_server(jira_data_sources['Apache'], disable_auth=True)
    projects = [project.raw['key'] for project in jira_auth.projects()]
    auth_projects = []
    for project in projects:
        if project == 'TESTTTTT':
            continue
        auth_count = jira_auth.search_issues(
            f'project="{project}"',
            startAt=0,
            maxResults=0,
            json_result=True)['total']
        non_auth_count = jira_non_auth.search_issues(
            f'project="{project}"',
            startAt=0,
            maxResults=0,
            json_result=True)['total']
        if auth_count != non_auth_count:
            auth_projects.append(project)
    return auth_projects


def main():
    # check_jira_urls()
    # download_issue_type_info()
    # download_issuelink_type_info()
    # download_issue_field_info()

    download_multiprocessed('Apache', jira_data_sources['Apache'])

    # # Update issue data
    # for jira_name in jira_data_sources:
    #     if jira_name in INVALID_JIRAS:
    #         continue
    #     download_multiprocessed(jira_name, jira_data_sources[jira_name])


if __name__ == '__main__':
    main()
