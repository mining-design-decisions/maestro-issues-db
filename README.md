# IssueLabels dataset

Use the following commands to dump the data from mongo in a file called `mongodump-IssueLabels.archive`:
```
docker exec -i mongo mongodump --db=IssueLabels --gzip --archive=mongodump-IssueLabels.archive
docker cp mongo:mongodump-IssueLabels.archive ./mongodump-IssueLabels.archive
```

Use the following commands to restore the dumped data:
```
docker cp ./mongodump-IssueLabels.archive mongo:/mongodump-IssueLabels.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-IssueLabels.archive --nsFrom "IssueLabels.*" --nsTo "IssueLabels.*"
```
