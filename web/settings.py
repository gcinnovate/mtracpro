# -*- coding: utf-8 -*-
import os
"""Default options for the application.
"""

DEBUG = False

SESSION_TIMEOUT = 3600  # 1 Hour

HASH_KEY = ''
VALIDATE_KEY = ''
ENCRYPT_KEY = ''
SECRET_KEY = ''
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# No of items to show on each age
PAGE_LIMIT = 25

# The time it takes to send an SMS schedule after it is created. It gives a chance to edit
SMS_OFFSET_TIME = 5

HMIS_033B_DATASET = 'C4oUitImBPK'
HMIS_033B_DATASET_ATTR_OPT_COMBO = 'HllvX50cXC0'  # DHIS2 v2.26 change
CARAMAL_DATASET = 'kzIS9qjcF6W'
CARAMAL_DATASET_ATTR_OPT_COMBO = 'bjDvmb4bfuf'  # DHIS2 v2.26 change

# The preferred content type for queuing data in Dispatcher2
PREFERRED_DHIS2_CONTENT_TYPE = 'xml'

# Whether to use the older version of webhooks of RapidPro when extracting values from flows
USE_OLD_WEBHOOKS = False

# position of indicator in its message form.
CASES_POSITIONS = {
    'ma': 0, 'dy': 1, 'sa': 2, 'af': 3, 'ae': 4, 'ab': 5, 'mg': 6, 'ch': 7, 'gw': 8,
    'me': 9, 'nt': 10, 'pl': 11, 'tf': 12, 'hb': 13, 'tb': 14, 'yf': 15, 'vf': 16, 'md': 17,
    'mb': 18, 'fb': 19, 'nd': 20,
    # other condition follow - luckily codes are unique
    'cg': 0, 'dg': 1, 'il': 2, 'ax': 3, 'hp': 4, 'dc': 5, 'lp': 6, 'oc': 7, 'bu': 8,
    'gw': 9, 'no': 10, 'hn': 11, 'ss': 12, 'sp': 13, 'dd': 14, 'pn': 15, 'tx': 16, 'tr': 17,
    'sc': 18, 'dp': 19, 'wc': 20, 'bc': 21, 'ka': 22, 'ns': 24, 'ar': 15
}
# Preferred delimiter for the message forms
DELIMITER = '.'

# Dictionary with length of each message form
KEYWORDS_DATA_LENGTH = {
    'cases': 16,
    'death': 18,
    'epc': 26,
    'epd': 26
}
# reports with commands - or irregular forms
REPORTS_WITH_COMMANDS = ['cases', 'death', 'epc', 'epd']

# Reporter groups to receive alert on thresholds and general alerts
THRESHOLD_ALERT_ROLES = ['Biostatistician']

GENERAL_ALERT_ROLES = ['Biostatistician']


def absolute(path):
    """Get the absolute path of the given file/folder.

    ``path``: File or folder.
    """
    import os
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(PROJECT_DIR, path))

config = {
    'db_name': 'mtrackpro',
    'db_host': 'localhost',
    'db_user': '',
    'db_passwd': '',
    'db_port': '5432',
    'logfile': '/tmp/mtrackpro-web.log',

    # Dipatcher 2
    'dispatcher2_queue_url': 'https://localhost:8003/queue?source=mtrack&destination=dhis2',
    'dispatcher2_username': 'admin',
    'dispatcher2_password': 'admin',
    'dispatcher2_source': 'mtrackpro',
    'dispatcher2_destination': 'dhis2',
    'dispatcher2_certkey_file': '/etc/dispatcher2/ca-cert.pem',
    'default-queue-status': 'pending',

    # DHIS2 Confs
    'dhis2_user': '',
    'dhis2_passwd': '',
    'base_url': 'http://hmis2.health.go.ug/api/analytics.csv?',
    'orgunits_url': 'http://hmis2.health.go.ug/api/organisationUnits',

    # sync_url is the service that creates/updates the facilities in mTracpro
    'sync_url': 'http://localhost:8080/create',
    'sync_user': 'admin',  # username for accessing sync service
    'sync_passwd': 'admin',  # password for sync service

    # facility levels as in DHI2 instance
    'hmis_033b_id': 'C4oUitImBPK',
    'levels': {
        'jTolsq2vJv8': 'HC II',
        'GM7GlqjfGAW': 'HC III',
        'luVzKLwlHJV': 'HC IV',
        'm0DN21c3PrY': 'General Hospital',
        'QEEIr51RGH8': 'NR Hospital',
        '2zEq4xZRpOp': 'RR Hospital',
        'YNsYaUOqAIs': 'Clinic',
    },

    # Network RegEx for Kannel logs
    'network_regex': {
        'mtn': '256(3[19]|7[78])',
        'airtel': '2567[05]',
        'africel': '25679',
        'utl': '25671',
        'others': '256(3[19]|41|7[015789])'  # opssite of
    },
    'shortcode': '6400',
    # 'default_api_uri': 'http://hiwa.LLIN.co.ug/api/v1/contacts.json',
    'smsurl': 'http://localhost:13013/cgi-bin/sendsms?username=foo&password=bar',
    'default_api_uri': 'http://localhost:8000/api/v1/contacts.json',
    'api_token': 'c8cde9dbbdda6f544018e9321d017e909b28ec51',
    'api_url': 'http://localhost:8000/api/v1/',
}

KEYWORD_SERVER_MAPPINGS = {
    'pmtct': 'dhis2_pmtct',
    'mcd': 'dhis2_pmtct',
    'lab': 'dhis2_pmtct',
    'ret': 'dhis2_pmtct',
    'ped': 'dhis2_pmtct',
    'creg': 'dhis2_pmtct',
    'stka': 'dhis2_pmtct',
    'stkc': 'dhis2_pmtct',
    'rcda': 'dhis2_pmtct',
    'rcdc': 'dhis2_alert',
    'alert': 'dhis2_alert',
    'update': 'dhis2_alert',
    'reg': 'dhis2_alert',
}

# Mapping of indicators to DHIS2 dataElements. as in dhis2_mtrack_indicators_mapping table
# XXX removed

# XML template for submitting data values using DHIS 2 API
XML_TEMPLATE = """
<dataValueSet xmlns="http://dhis2.org/schema/dxf/2.0" dataSet="V1kJRs8CtW4" completeDate="%(completeDate)s" period="%(period)s" orgUnit="%(orgUnit)s" attributeOptionCombo="gGhClrV5odI">
<dataValues>
    %(dataValues)s
</dataValues>
</dataValueSet>
"""

DEFAULT_DATA_VALUES = {
    'cases': "<dataValue dataElement='fclvwNhzu7d' categoryOptionCombo='gGhClrV5odI' value='0' />",
    'death': "<dataValue dataElement='YXIu5CW9LPR' categoryOptionCombo='gGhClrV5odI' value='0' />"
}

# Json template for submitting data values using DHIS 2 API
JSON_TEMPLATE = {
    'dataSet': 'V1kJRs8CtW4',
    'completeDate': '',
    'period': '',
    'orgUnit': '',
    'dataValues': []
}
SEND_ALERTS = False

# the order of fields in the reporter upload excel file
EXCEL_UPLOAD_ORDER = {
    'name': 0,
    'telephone': 1,
    'alternate_tel': 2,
    'role': 3,
    'subcounty': 4,
    'parish': 5,
    'village': 6,
    'village_code': 7
}

# HMIS reports for Data Entry page
HMIS_REPORTS = [
    {
        'name': 'HMIS 033B Report',
        'keywords': ['act', 'opd', 'test', 'treat', 'rdt', 'qun', 'cases', 'death']
    },
    {
        'name': 'CARAMAL Report',
        'keywords': ['car', 'ras']
    }
]

# keyword/forms representing complete reports
COMPLETE_REPORTS_KEYWORDS = ['cases', 'death', 'tra', 'mat', 'arv', 'apt']
TEXT_INDICATORS = []

# contacts for the caramal research team in the three pilot districts. used for reminders
CARAMAL_RESEARCH_TEAM = {
    'Kole': {
        'Aboke': '',
    },
    'Oyam': {
        'Aber': '',
        'Abok': '',
    },
    'Apac': {
        'Abongomola': '',
        'Aduku': '',
    },
}

try:
    from local_settings import *
except ImportError:
    pass
