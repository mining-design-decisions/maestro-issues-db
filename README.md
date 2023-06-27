# VM (debian 11)
Get your public ssh-key: `cat .ssh/id_rsa.pub`

Setup SSH with a new user:
```
ssh root@ip
passwd root
sudo adduser USERNAME
sudo su - USERNAME
mkdir .ssh
chmod 700 .ssh
touch .ssh/authorized_keys
chmod 600 .ssh/authorized_keys
```
Add you public ssh key with:
```
nano .ssh/authorized_keys
```
Continue
```
exit
usermod -aG sudo USERNAME
exit
ssh USERNAME@ip
```
Install docker (https://docs.docker.com/engine/install/debian/ and https://docs.docker.com/engine/install/linux-postinstall/)

Setup for git clone
```
sudo reboot
ssh USERNAME@ip
ssh-keygen -t rsa
cat .ssh/id_rsa.pub
```
Add this public key to GitHub
```
git clone git@github.com:GWNLekkah/issue-labels.git
```

Get SSL certificate (https://certbot.eff.org/instructions?ws=webproduct&os=debianbuster)
```
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot certonly --standalone
sudo cp /etc/letsencrypt/live/issues-db.nl/fullchain.pem issue-labels/issues-db-api/fullchain.pem
sudo cp /etc/letsencrypt/live/issues-db.nl/privkey.pem issue-labels/issues-db-api/privkey.pem
cd issue-labels/
```
Get your OpenSSL secret:
```
openssl rand -hex 32
```
Open the following file:
```
nano issues-db-api/app/config.py
```
Now add the following content to the file:
```
SECRET_KEY = 'SECRET_FROM_OPENSSL'
SSL_KEYFILE = 'privkey.pem'
SSL_CERTFILE = 'fullchain.pem'
```
Ready to boot up the issues-db-api and databases
```
sudo docker compose up --build -d
```

# Download data
First setup Python

Download the JiraRepos archive and restore it:
```
docker cp ./mongodump-JiraRepos_2023-03-07-16:00.archive mongo:/mongodump-JiraRepos.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-JiraRepos.archive --nsFrom "JiraRepos.*" --nsTo "JiraRepos.*"
```
Download the MiningDesignDecisions archive and restore it:
```
docker cp ./mongodump-MiningDesignDecisions.archive mongo:/mongodump-MiningDesignDecisions.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-MiningDesignDecisions.archive --nsFrom "MiningDesignDecisions.*" --nsTo "MiningDesignDecisions.*"
```

# Dump data

JiraRepos:
```
docker exec -i mongo mongodump --db=MiningDesignDecisions --gzip --archive=mongodump-MiningDesignDecisions.archive
docker cp mongo:mongodump-MiningDesignDecisions.archive ./mongodump-MiningDesignDecisions.archive
```

MiningDesignDecisions:
```
docker exec -i mongo mongodump --db=JiraRepos --gzip --archive=mongodump-JiraRepos.archive
docker cp mongo:mongodump-JiraRepos.archive ./mongodump-JiraRepos.archive
```

# Search engine
```
git clone git@github.com:GWNLekkah/add-search-engine.git
cd add-search engine
sudo cp /etc/letsencrypt/live/issues-db.nl/fullchain.pem pylucene/fullchain.pem
sudo cp /etc/letsencrypt/live/issues-db.nl/privkey.pem pylucene/privkey.pem
sudo docker compose up --build -d
```

# SSH Tunneling
In case you want to access the mongo-express UI, you need to tunnel via ssh:
```
ssh -L 8082:issues-db.nl:8081 arjan@issues-db.nl
```
