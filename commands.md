* Check process by process id

    ps - p 1

* Check process by command name

    ps -C postgres

    ps -C systemd

* Check process by parent process id

    ps --ppid 1

* Check process by user

    ps -U postgres
    ps -U root
    ps -U akshar

* Format output to show all columns. Like user, process id, parent process id, command, arguments etc.

Use the `-F` argument.

    ps -U root -F

    ps -C sshd -F

    ps -p 1 -F

`TIME` column shows the CPU time used by the process.

* Find everything about the ssh process

    ps -U root -F | grep ssh

This tells the pid of the ssh process.

The following systemctl command gives the same pid as well.

    sudo systemctl status ssh.service


## Local Setup

Postgres start

    docker container run --name ramayanquiz-postgres -p 5432:5432 --volume ramayanquiz:/var/lib/postgresql/data postgres

Mongo start

    docker container run --name ramayanquiz-mongo -p 27017:27017 --volume ramayanquiz-mongo:/data/db mongo

RabbitMQ start

    docker run --name ramayanquiz-rabbitmq -p 5672:5672 -p 15672:15672 -v ramayanquiz-rabbitmq:/var/lib/rabbitmq rabbitmq:3.13-management

Application server start

    docker run --name ramayanquiz-server -p 8002:8000 ramayanquiz


## Server

Application server start

    docker run -d --name ramayanquiz --network="host" -v .:/app ramayanquiz
