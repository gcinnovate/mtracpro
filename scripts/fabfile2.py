# from fabric import task, Connection, SerialGroup as Group
from fabric import task


@task
def deploy(c):
    c.run('cd /var/www/mtracpro_prod/mtracpro')
    c.run('git pull origin master')
    c.run('sudo supervisorctl restart mtracpro celery')
    c.run('sudo supervisorctl status')

# for connection in Group('web01', 'web02'):
#    deploy(connection)

# $ fab --list
# $ fab -H web01,web02 deploy
