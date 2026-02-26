# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from webapp.app.controllers.main_handler import Index, Logout
from webapp.app.controllers.api import (
    Location, LocationChildren, SubcountyLocations,
    DistrictFacilities, LocationFacilities, FacilityReporters,
    Cases, Deaths, OrderMessage, Dhis2Queue, Test, ReportsThisWeek,
    QueueForDhis2InstanceProcessing, ReporterAPI, StartSurvey, Bulletin
)
from webapp.app.controllers.api2 import (
    LocationsEndpoint, ReportersXLEndpoint,
    CreateFacility, ReportForms, IndicatorHtml,
    FacilitySMS, SendSMS, RequestDetails, SendBulkSMS,
    DeleteRequest, DeleteServer, ServerDetails,
    RetryFailed, SyncFacilities
)
from webapp.app.controllers.api3 import EditReport, ReportingWeek, ReporterHistoryApi
from webapp.app.controllers.api4 import ReportersUploadAPI
from webapp.app.controllers.api5 import CaramalReminders
from webapp.app.controllers.api6 import QueueRejectedReports
from webapp.app.controllers.api7 import AnonymousReports, AnonymousReportDetails, AnonReport
from webapp.app.controllers.api8 import IndicatorsAPI, ReportingStatus, Dispatch, SendAlert
from webapp.app.controllers.reporters_handler import Reporters
from webapp.app.controllers.users_handler import Users
from webapp.app.controllers.groups_handler import Groups
from webapp.app.controllers.permissions_handler import Permissions
from webapp.app.controllers.dashboard_handler import Dashboard
from webapp.app.controllers.approve_handler import Approve
from webapp.app.controllers.auditlog_handler import AuditLog
from webapp.app.controllers.smslog_handler import SMSLog
from webapp.app.controllers.requests_handler import Requests
from webapp.app.controllers.completed_handler import Completed
from webapp.app.controllers.failed_handler import Failed
from webapp.app.controllers.ready_handler import Ready
from webapp.app.controllers.search_handler import Search
from webapp.app.controllers.appsettings_handler import AppSettings
from webapp.app.controllers.dataentry_handler import DataEntry
from webapp.app.controllers.polls_handler import Polls, PollResponses, StartPoll, DeletePoll, StopPoll
from webapp.app.controllers.settings_handler import Settings
from webapp.app.controllers.forgotpass_handler import ForgotPass
from webapp.app.controllers.facilities_handler import Facilities
from webapp.app.controllers.downloads_handler import Downloads
from webapp.app.controllers.adminunits_handler import AdminUnits
from webapp.app.controllers.fsync_handler import FSync
from webapp.app.controllers.messagehistory_handler import MessageHistory
from webapp.app.controllers.facilityreports_handler import FacilityReports
from webapp.app.controllers.hotline_handler import Hotline
from webapp.app.controllers.caramal_handler import CaramalReports
from webapp.app.controllers.archive_handler import Archive
from webapp.app.controllers.indicators_handler import Indicators
from webapp.app.controllers.rejected_handler import Rejected
from webapp.app.controllers.schedules_handler import Schedules
from webapp.app.controllers.interventions_handler import Interventions, Preview
from webapp.app.controllers.adminunits_handler import (
    GetTree, SearchTree, GetNodeDetails, EditNode, MoveNode, RenameNode, DeleteNode, SyncHierarchy,
    SyncFacility, FacilityDetails)
from webapp.app.controllers.requests_api import RequestsAPI
from webapp.app.controllers.servers_api import ServersAPI, ServerSuspend, ServerResume

# from app.controllers.transfers_handler import Transfers
# from app.controllers.queue_mgt_handler import QueueManagement

URLS = (
    r'^/', Index,
    r'/smslog', SMSLog,
    r'/adminunits', AdminUnits,
    r'/downloads', Downloads,
    r'/reporters', Reporters,
    r'/approve', Approve,
    r'/hotline', Hotline,
    r'/caramalreports', CaramalReports,
    r'/caramalreminders', CaramalReminders,
    r'/interventions', Interventions,
    r'/facilities', Facilities,
    r'/auditlog', AuditLog,
    r'/settings', Settings,
    r'/fsync', FSync,
    r'/schedules', Schedules,
    r'/dashboard', Dashboard,
    r'/users', Users,
    r'/groups', Groups,
    r'/permissions', Permissions,
    r'/logout', Logout,
    r'/forgotpass', ForgotPass,
    r'/create', CreateFacility,
    r'/dataentry', DataEntry,
    r'/polling', Polls,
    r'/startpoll/(\d+)/?', StartPoll,
    r'/stoppoll/(\d+)/?', StopPoll,
    r'/deletepoll/(\d+)/?', DeletePoll,
    r'/archive', Archive,
    r'/rejected', Rejected,
    r'/messagehistory/\+?(\w+)/?', MessageHistory,
    r'/facilityreports/(\w+)/?', FacilityReports,
    # r'/transfers', Transfers,
    # Dispatcher2 URIs
    r'/requests', Requests,
    r'/completed', Completed,
    r'/failed', Failed,
    r'/search', Search,
    r'/ready', Ready,
    r'/appsettings', AppSettings,
    r'/indicators', Indicators,
    # r'/management', QueueManagement,
    # API stuff follows
    r'/cases', Cases,  # cases flow
    r'/deaths', Deaths,  # deaths flow
    r'/ordermessage/(\w+)/?', OrderMessage,
    r'/errors', QueueRejectedReports,  # intended to save messages that ran into errors in rapidPro
    r'/dhis2queue', Dhis2Queue,  # queue reports in dispatcher2
    r'/dhis2instancequeue', QueueForDhis2InstanceProcessing,  # queue reports in dispatcher2
    r'/api/v1/dispatch', Dispatch,  # Sends to other servers/apps via Dispatcher2  -> controllers.api8.py
    r'/sendalert', SendAlert,
    r'/pollresponses', PollResponses,
    r'/test', Test,
    r'/api/v1/preview', Preview,  # give status of reporters status
    r'/api/v1/status/(\w+)/?', ReportingStatus,  # give status of reporters status
    r'/api/v1/anonreport/(\d+)/?', AnonReport,
    r'/api/v1/anonymousreports', AnonymousReports,
    r'/api/v1/anonymousreport_details/(\d+)/?', AnonymousReportDetails,
    r'/api/v1/loc_children/(\d+)/?', LocationChildren,
    r'/api/v1/district_facilities/(\d+)/?', DistrictFacilities,
    r'/api/v1/facility_reporters/(\d+)/?', FacilityReporters,
    r'/api/v1/loc_facilities/(\d+)/?', LocationFacilities,
    r'/api/v1/location/(\d+)/?', Location,
    r'/api/v1/subcountylocations/(\d+)/?', SubcountyLocations,
    r'/api/v1/locations_endpoint/(\w+)/?', LocationsEndpoint,  # controllers.api2.py
    r'/api/v1/reporters_xlendpoint', ReportersXLEndpoint,
    r'/api/v1/reportsthisweek/(\w+)/?', ReportsThisWeek,
    r'/api/v1/reportforms/(\w+)/?', ReportForms,
    r'/api/v1/indicatorhtml/(\w+)/?', IndicatorHtml,
    r'/api/v1/facilitysms/(\d+)/?', FacilitySMS,
    r'/api/v1/facility_details/(\d+)/?', FacilityDetails,
    r'/api/v1/sendsms', SendSMS,
    r'/api/v1/sendbulksms', SendBulkSMS,
    r'/api/v1/request_details/(\d+)/?', RequestDetails,
    r'/api/v1/server_details/(\d+)/?', ServerDetails,
    r'/api/v1/request_del/(\d+)/?', DeleteRequest,
    r'/api/v1/requests/retry_failed/?', RetryFailed,
    r'/api/v1/server_del/(\d+)/?', DeleteServer,  # controllers.api2.py
    r'/api/v1/editreport/(\d+)/?', EditReport,  # for retrospective report edits
    r'/api/v1/reportingweek/?', ReportingWeek,
    r'/api/v1/reporter/(\+?\w+)/?', ReporterAPI,
    r'/api/v1/bulletin/(\+?\w+)/?', Bulletin,
    r'/api/v1/startsurvey/?', StartSurvey,
    r'/reportersupload', ReportersUploadAPI,
    r'/api/v1/reporterhistory/(\+?\w+)/?', ReporterHistoryApi,
    r'/api/v1/indicators', IndicatorsAPI,
    r'/api/v1/requests', RequestsAPI,
    r'/api/v1/servers', ServersAPI,
    r'/api/v1/servers/(\d+)/suspend', ServerSuspend,
    r'/api/v1/servers/(\d+)/resume', ServerResume,
    # Hierarchical tree stuff
    r'/api/tree', GetTree,
    r'/api/search', SearchTree,
    r'/api/details', GetNodeDetails,
    r'/api/edit', EditNode,
    r'/api/move', MoveNode,
    r'/api/rename', RenameNode,
    r'/api/node/delete', DeleteNode,
    r'/api/sync_hierarchy', SyncHierarchy,
    r'/api/sync_facility/([a-zA-Z][a-zA-Z0-9]{10})/?', SyncFacility,
    r'/api/sync_facilities', SyncFacilities,
)
