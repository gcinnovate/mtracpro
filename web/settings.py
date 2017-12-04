# -*- coding: utf-8 -*-

"""Default options for the application.
"""

DEBUG = False

SESSION_TIMEOUT = 3600  # 1 Hour

HASH_KEY = ''
VALIDATE_KEY = ''
ENCRYPT_KEY = ''
SECRET_KEY = ''

PAGE_LIMIT = 25

SMS_OFFSET_TIME = 5

HMIS_033B_DATASET = 'V1kJRs8CtW4'
HMIS_033B_DATASET_ATTR_OPT_COMBO = 'gGhClrV5odI'  # DHIS2 v2.26 change
PREFERRED_DHIS2_CONTENT_TYPE = 'xml'

CASES_POSITIONS = {
    'ma': 0, 'dy': 1, 'sa': 2, 'af': 3, 'ae': 4, 'ab': 5, 'mg': 6, 'ch': 7, 'gw': 8,
    'me': 9, 'nt': 10, 'vf': 11, 'pl': 12, 'tf': 13, 'yf': 14, 'tb': 15, 'md': 16, 'pd': 17
}
DELIMITER = '.'
KEYWORDS_DATA_LENGTH = {
    'cases': 16,
    'death': 18,
}
REPORTS_WITH_COMMANDS = ['cases', 'death']


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
    'dispatcher2_certkey_file': '/etc/dispatcher2/ca-cert.pem',

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
    'hmis_033b_id': 'V1kJRs8CtW4',
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

MAPPING = {
    'apt_emtct_expected': {
        'descr': 'Expected eMTCT Mothers on Appointment',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'xVpHSWaIBEX'
    },
    'apt_emtct_missed': {
        'descr': 'eMTCT Missed Appointments',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'LYT11E96lC5'
    },
    'apt_opd_new': {
        'descr': 'OPD New Attendees',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'xqSBj2KUlas'
    },
    'apt_opd_total': {
        'descr': 'OPT Total Attendence',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'xb4g6Zf7fAT'
    },
    'arv_emtct': {
        'descr': 'ARVs (Fixed - DC eMTCT)',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'xgSJLvdm2cQ'
    },
    'arv_nevirapine': {
        'descr': 'Nevirapine Therapy',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'JPVp2yLEimL'
    },
    'arv_hiv_screening_test_kits': {
        'descr': 'HIV screening test kits',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'kteQimFQJom'
    },
    'cases_ab': {
        'descr': 'Cases of Animal Bites',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'mdIPCPfqXaJ'},
    'cases_ae': {
        'descr': 'Cases of Adverse Events Following Immunization',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'fTwT8uX9Uto'
    },
    'cases_af': {
        'descr': 'Cases of Acute Flacid Paralysis',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'U7cokRIptxu'
    },
    'cases_ch': {
        'descr': 'Cases of Cholera',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'FPsN2bDpRru'
    },
    'cases_dy': {
        'descr': 'Cases of Dysentery',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'NoJfAIcxjSY'
    },
    'cases_gw': {
        'descr': 'Cases of Guinea Worm',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'hzGgkiOjfRs'
    },
    'cases_id': {
        'descr': 'Cases of Other Emerging Infectious Diseases',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'ZZrhG7CYNjy'
    },
    'cases_ma': {
        'descr': 'Cases of Malaria',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'fclvwNhzu7d'
    },
    'cases_me': {
        'descr': 'Cases of Measles',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'v8HuPNb03yq'
    },
    'cases_mg': {
        'descr': 'Cases of Bacterial Meningitis',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'JxUexqKeXtZ'},
    'cases_nt': {
        'descr': 'Cases of Neonatal Tetanus',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'euf2TqlswFp'
    },
    'cases_pl': {
        'descr': 'Cases of Plague',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'peyFcHisgZB'
    },
    'cases_rb': {
        'descr': 'Cases of Rabies',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'tTGAElxDIWg'
    },
    'cases_sa': {
        'descr': 'Cases of Severe Acute Respiratory Infection',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'MHtpmIQEnyc'
    },
    'cases_tb': {
        'descr': 'Presumptive Multi Drug Resistance (MDR) TB',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'yzdPKhvgeXq'},
    'cases_tf': {
        'descr': 'Cases of Typhoid Fever',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'IkI01xB7RIi'
    },
    'cases_vf': {
        'descr': 'Cases of Other Viral Hemorrhagic Fevers',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'BMJMdxh1Loy'
    },
    'cases_yf': {
        'descr': 'Cases of Yellow Fever',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'OE8baEzA2Cq'
    },
    'death_ab': {
        'descr': 'Deaths from Animal Bites',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'UKYPpKnSBK4'
    },
    'death_ae': {
        'descr': 'Deaths from Adverse Events Following Immunization',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'k2dUb4N7D0D'
    },
    'death_af': {
        'descr': 'Deaths from Acute Flacid Paralysis',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'XzYd9m4XaKS'
    },
    'death_ch': {
        'descr': 'Deaths from Cholera',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'QP9yftzrkne'
    },
    'death_dy': {
        'descr': 'Deaths from Dysentery',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'JTc25LIvtQb'
    },
    'death_gw': {
        'descr': 'Deaths from Guinea Worm',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'yvbPC5zDb3c'
    },
    'death_id': {
        'descr': 'Deaths from Other Emerging Infectious Diseases',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'qHSErXOlcf3'
    },
    'death_ma': {
        'descr': 'Deaths from Malaria',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'YXIu5CW9LPR'
    },
    'death_md': {
        'descr': 'Maternal deaths',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'ck3jFjr8fOT'
    },
    'death_me': {
        'descr': 'Deaths from Measles',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'tjTnFJ1QdVz'
    },
    'death_mg': {
        'descr': 'Deaths from Bacterial Meningitis',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'r3xIBQaeLsT'},
    'death_nt': {
        'descr': 'Deaths from Neonatal Tetanus',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'tIh9TQxGOJU'
    },
    'death_pd': {
        'descr': 'Perinatal deaths',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'nG5hrCX3vyP'
    },
    'death_pl': {
        'descr': 'Deaths from Plague',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'hBcX7S7xBcu'
    },
    'death_rb': {
        'descr': 'Deaths from Rabies',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'Dy90lwS6c6x'
    },
    'death_sa': {
        'descr': 'Deaths from Severe Acute Respiratory Infection',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'qdZbdsCpIr7'
    },
    'death_tb': {
        'descr': 'Presumptive Multi Drug Resistance (MDR) TB',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'eEruojUV6Jh'
    },
    'death_tf': {
        'descr': 'Deaths from Typhoid Fever',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'OMxmmYvvLai'
    },
    'death_vf': {
        'descr': 'Deaths from Other Viral Hemorrhagic Fevers',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'BX2PYPKm8F9'
    },
    'death_yf': {
        'descr': 'Deaths from Yellow Fever',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'w3mO7SZdbb8'
    },
    'mat_microscopy_neg_treated': {
        'descr': 'Microscopy negative cases treated',
        'dhis2_combo_id': 'TTwU8Bv4fKm',
        'dhis2_id': 'ZgPtploqq0L'
    },
    'mat_microscopy_positive': {
        'descr': 'Microscopy positive cases',
        'dhis2_combo_id': '3rYpFjLrrYa',
        'dhis2_id': 'KPmTI3TGwZw'
    },
    'mat_microscopy_pos_treated': {
        'descr': 'Microscopy positive cases treated',
        'dhis2_combo_id': 'vp37EZVg3xG',
        'dhis2_id': 'ZgPtploqq0L'
    },
    'mat_microscopy_tested': {
        'descr': 'Microscopy tested cases',
        'dhis2_combo_id': 't8Jv78lnSbU',
        'dhis2_id': 'KPmTI3TGwZw'
    },
    'mat_not_tested_treated': {
        'descr': 'Not tested cases treated',
        'dhis2_combo_id': 'w16OBdsg4b7',
        'dhis2_id': 'ZgPtploqq0L'
    },
    'mat_rdt_neg_treated': {
        'descr': 'RDT negative cases treated',
        'dhis2_combo_id': 'NfJyyb1eBaw',
        'dhis2_id': 'ZgPtploqq0L'
    },
    'mat_rdt_positive': {
        'descr': 'RDT positive cases',
        'dhis2_combo_id': 'PfdPCxOoiBj',
        'dhis2_id': 'KPmTI3TGwZw'
    },
    'mat_rdt_pos_treated': {
        'descr': 'RDT positive cases treated',
        'dhis2_combo_id': 'QOWAmZ7jBno',
        'dhis2_id': 'ZgPtploqq0L'
    },
    'mat_rdt_tesed': {
        'descr': 'RDT tested cases',
        'dhis2_combo_id': 'kcXY5cWAOsB',
        'dhis2_id': 'KPmTI3TGwZw'
    },
    'mat_suspected_malaria': {
        'descr': 'Suspected Malaria (fever)',
        'dhis2_combo_id': '3W3d2AqT4Aq',
        'dhis2_id': 'KPmTI3TGwZw'
    },
    'tra_act_tablets': {
        'descr': 'ACT (Tablets)',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'Ju0Cann41Ul'
    },
    'tra_amoxcilline': {
        'descr': 'Amoxcilline',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'tFrWdigZ4oo'
    },
    'tra_depo_provera': {
        'descr': 'Depo - Provera',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'v6ACxYNPIvm'
    },
    'tra_fansidar': {
        'descr': 'Fansidar',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'fX6A6NO18pY'
    },
    'tra_iv_artesunate': {
        'descr': 'IV artesunate',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'O2OrXuZo4hB'
    },
    'tra_measles_vaccine': {
        'descr': 'Measles Vaccine',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'DgeykDdSLzI'
    },
    'tra_ors_sackets': {
        'descr': 'ORS (Sackets)',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'zmimiDOJwaf'
    },
    'tra_rdt_malaria': {
        'descr': 'Malaria RDTs',
        'dhis2_combo_id': 'gGhClrV5odI',
        'dhis2_id': 'CzsKMvQDwMV'
    }
}

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

JSON_TEMPLATE = {
    'dataSet': 'V1kJRs8CtW4',
    'completeDate': '',
    'period': '',
    'orgUnit': '',
    'dataValues': []
}

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
HMIS_REPORTS = [
    {
        'name': 'HMIS 033B Report',
        'keywords': ['act', 'opd', 'test', 'treat', 'rdt', 'qun', 'cases', 'death']
    }
]
COMPLETE_REPORTS_KEYWORDS = ['cases', 'death', 'tra', 'mat', 'arv', 'apt']

try:
    from local_settings import *
except ImportError:
    pass
