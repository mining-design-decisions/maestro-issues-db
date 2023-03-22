import os
from pymongo import MongoClient
import gridfs

# mongo_client = MongoClient('mongodb://localhost:27017')
mongo_client = MongoClient(os.environ['MONGO_URL'])

jira_repos_db = mongo_client['JiraRepos']
fs = gridfs.GridFS(mongo_client['ModelsSaveFiles'])
embeddings_fs = gridfs.GridFS(mongo_client['EmbeddingsFS'])

manual_labels_collection = mongo_client['IssueLabels']['ManualLabels']
projects_collection = mongo_client['IssueLabels']['Projects']
issue_links_collection = mongo_client['IssueLabels']['IssueLinks']
model_info_collection = mongo_client['Models']['ModelInfo']
users_collection = mongo_client['Users']['Users']
embeddings_collection = mongo_client['DeepLearning']['Embeddings']
