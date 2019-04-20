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

api_token = '90532182de6947ed4d3d202d95eb0e280aa305c5'
apiv2_endpoint = 'http://localhost:8000/api/v2/'  # with trailing slash(/)
