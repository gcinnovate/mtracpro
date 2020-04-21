BROKER_URL = 'redis://localhost:6379/5'

db_conf = {
    'host': 'localhost',
    'name': 'mtrackpro2',
    'user': 'postgres',
    'passwd': 'postgres',
    'port': '5432'
}

# RapidPro Flow uuids to choose from when running a poll
poll_flows = {
    # Yes/No
    'yn': ['e6de8717-7f83-4ad1-a4e1-b48b76e1bf2f'],
    # Free Text
    't': [],
    # Numeric
    'n': []
}
config = {
    # Dipatcher 2
    'dispatcher2_queue_url': 'http://localhost:9191/queue?',
    'dispatcher2_username': 'admin',
    'dispatcher2_password': 'admin',
    'dispatcher2_source': 'mtrackpro',
    'dispatcher2_destination': 'dhis2',
    'dispatcher2_certkey_file': '/etc/dispatcher2/ssl.pem',
    'default-queue-status': 'pending',
}

api_token = '90532182de6947ed4d3d202d95eb0e280aa305c5'
apiv2_endpoint = 'http://localhost:8000/api/v2/'  # with trailing slash(/)

# SAMBA File Sever Settings
SMB_SERVER_NAME = 'moh-svr-mpro-haproxy-02'
SMB_SERVER_IP = 'localhost'
SMB_DOMAIN_NAME = ''
SMB_PORT = 445
SMB_USER = 'ssekiwere'
SMB_PASSWORD = 'samba'
SMB_CLIENT_HOSTNAME = 'moh-svr-mpro-web-01'
SMB_SHARED_FOLDER = 'share'

try:
    from local_celeryconfig import *
except ImportError:
    pass
