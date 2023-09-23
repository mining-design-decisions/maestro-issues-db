# Maestro Issues Database (API)
This repository contains the issues database and its API of Maestro. The Mongo archives can be downloaded from here:
[https://zenodo.org/record/8225601](https://zenodo.org/record/8372644). Note that this version also contains a lite
variant of the MiningDesignDecisions archive. This lite variant only contains the best trained model (BERT) and no
other files or embeddings.

## Setup
The setup process is described below. Note that, because it uses HTTPS, it needs an SSL certificate (fullchain.pem and
privkey.pem).
```
git clone git@github.com:mining-design-decisions/maestro-issues-db.git
sudo cp /etc/letsencrypt/live/issues-db.nl/fullchain.pem maestro-issues-db/issues-db-api/fullchain.pem
sudo cp /etc/letsencrypt/live/issues-db.nl/privkey.pem maestro-issues-db/issues-db-api/privkey.pem
cd maestro-issues-db/
```

Get your OpenSSL secret:
```
openssl rand -hex 32
```

Create and open the following file:
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

(Optional) In case you want to dump the data from the JiraRepos database:
```
docker exec -i mongo mongodump --db=MiningDesignDecisions --gzip --archive=mongodump-MiningDesignDecisions.archive
docker cp mongo:mongodump-MiningDesignDecisions.archive ./mongodump-MiningDesignDecisions.archive
```

(Optional) In case you want to dump the data from the MiningDesignDecisions database:
```
docker exec -i mongo mongodump --db=JiraRepos --gzip --archive=mongodump-JiraRepos.archive
docker cp mongo:mongodump-JiraRepos.archive ./mongodump-JiraRepos.archive
```

## VM Setup (debian 11)
One of the main strengths of this database is the fact that it can be run on a cloud VM, in order to have an online
shared database. Hence, this section contains the setup process for a VM (debian 11).

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
Install docker (https://docs.docker.com/engine/install/debian/ and
https://docs.docker.com/engine/install/linux-postinstall/) and install Python3.10

Setup for git clone
```
sudo reboot
ssh USERNAME@ip
ssh-keygen -t rsa
cat .ssh/id_rsa.pub
```
Add this public key to GitHub
```
git clone git@github.com:mining-design-decisions/maestro-issues-db.git
```

Get SSL certificate (https://certbot.eff.org/instructions?ws=webproduct&os=debianbuster)
```
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot certonly --standalone
sudo cp /etc/letsencrypt/live/issues-db.nl/fullchain.pem maestro-issues-db/issues-db-api/fullchain.pem
sudo cp /etc/letsencrypt/live/issues-db.nl/privkey.pem maestro-issues-db/issues-db-api/privkey.pem
cd maestro-issues-db/
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

(Optional) In case you want to dump the data from the JiraRepos database:
```
docker exec -i mongo mongodump --db=MiningDesignDecisions --gzip --archive=mongodump-MiningDesignDecisions.archive
docker cp mongo:mongodump-MiningDesignDecisions.archive ./mongodump-MiningDesignDecisions.archive
```

(Optional) In case you want to dump the data from the MiningDesignDecisions database:
```
docker exec -i mongo mongodump --db=JiraRepos --gzip --archive=mongodump-JiraRepos.archive
docker cp mongo:mongodump-JiraRepos.archive ./mongodump-JiraRepos.archive
```

In case you want to access the mongo-express UI securely, you need to tunnel via ssh:
```
ssh -L 8082:issues-db.nl:8081 arjan@issues-db.nl
```
