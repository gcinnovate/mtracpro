# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from app.controllers.main_handler import Index, Logout
from app.controllers.api import (
    Location, LocationChildren, SubcountyLocations,
    DistrictFacilities, LocationFacilities, FacilityReporters,
    Cases, Deaths, OrderMessage, Dhis2Queue, Test, ReportsThisWeek,
    QueueForDhis2InstanceProcessing, ReporterAPI, StartSurvey
)
from app.controllers.api2 import (
    LocationsEndpoint, ReportersXLEndpoint,
    CreateFacility, ReportForms, IndicatorHtml,
    FacilitySMS, SendSMS, RequestDetails, SendBulkSMS,
    DeleteRequest, DeleteServer, ServerDetails
)
from app.controllers.api3 import EditReport, ReportingWeek, ReporterHistoryApi
from app.controllers.api4 import ReportersUploadAPI
from app.controllers.api5 import CaramalReminders
from app.controllers.api6 import QueueRejectedReports
from app.controllers.api7 import AnonymousReports, AnonymousReportDetails, AnonReport
from app.controllers.api8 import IndicatorsAPI, ReportingStatus, Dispatch, SendAlert
from app.controllers.reporters_handler import Reporters
from app.controllers.users_handler import Users
from app.controllers.groups_handler import Groups
from app.controllers.permissions_handler import Permissions
from app.controllers.dashboard_handler import Dashboard
from app.controllers.approve_handler import Approve
from app.controllers.auditlog_handler import AuditLog
from app.controllers.smslog_handler import SMSLog
from app.controllers.requests_handler import Requests
from app.controllers.completed_handler import Completed
from app.controllers.failed_handler import Failed
from app.controllers.ready_handler import Ready
from app.controllers.search_handler import Search
from app.controllers.appsettings_handler import AppSettings
from app.controllers.dataentry_handler import DataEntry
from app.controllers.polls_handler import Polls, PollResponses, StartPoll, DeletePoll, StopPoll
from app.controllers.settings_handler import Settings
from app.controllers.forgotpass_handler import ForgotPass
from app.controllers.facilities_handler import Facilities
from app.controllers.downloads_handler import Downloads
from app.controllers.adminunits_handler import AdminUnits
from app.controllers.fsync_handler import FSync
from app.controllers.messagehistory_handler import MessageHistory
from app.controllers.facilityreports_handler import FacilityReports
from app.controllers.hotline_handler import Hotline
from app.controllers.caramal_handler import CaramalReports
from app.controllers.archive_handler import Archive
from app.controllers.indicators_handler import Indicators
from app.controllers.rejected_handler import Rejected
from app.controllers.schedules_handler import Schedules
from app.controllers.interventions_handler import Interventions

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
    # Dispatcher2 URIs
    r'/requests', Requests,
    r'/completed', Completed,
    r'/failed', Failed,
    r'/search', Search,
    r'/ready', Ready,
    r'/appsettings', AppSettings,
    r'/indicators', Indicators,
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
    r'/api/v1/sendsms', SendSMS,
    r'/api/v1/sendbulksms', SendBulkSMS,
    r'/api/v1/request_details/(\d+)/?', RequestDetails,
    r'/api/v1/server_details/(\d+)/?', ServerDetails,
    r'/api/v1/request_del/(\d+)/?', DeleteRequest,
    r'/api/v1/server_del/(\d+)/?', DeleteServer,  # controllers.api2.py
    r'/api/v1/editreport/(\d+)/?', EditReport,  # for retrospective report edits
    r'/api/v1/reportingweek/?', ReportingWeek,
    r'/api/v1/reporter/(\+?\w+)/?', ReporterAPI,
    r'/api/v1/startsurvey/?', StartSurvey,
    r'/reportersupload', ReportersUploadAPI,
    r'/api/v1/reporterhistory/(\+?\w+)/?', ReporterHistoryApi,
    r'/api/v1/indicators', IndicatorsAPI,

)
