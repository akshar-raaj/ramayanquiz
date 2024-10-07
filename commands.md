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