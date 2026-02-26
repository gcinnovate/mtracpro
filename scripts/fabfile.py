#!/usr/bin/env python
from fabric import task


@task
def deploy(c):
    c.run('cd /var/www/mtracpro_prod/mtracpro && git pull origin master')
    # c.run('git pull origin master')
    c.run('sudo supervisorctl restart mtracpro mtracpro_celery')
    c.run('sudo supervisorctl status')


@task
def restart(c):
    c.run('sudo supervisorctl restart mtracpro mtracpro_celery')
    c.run('sudo supervisorctl status')


@task
def restartall(c):
    c.run('sudo supervisorctl restart all')
    c.run('sudo supervisorctl status')


@task
def status(c):
    c.run('sudo supervisorctl status')

# $ fab --list
# $ fab -H web01,web02 deploy
