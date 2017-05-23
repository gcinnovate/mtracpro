# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from app.controllers.main_handler import Index, Logout
from app.controllers.api import Location, LocationChildren, SubcountyLocations
from app.controllers.api import DistrictFacilities, LocationFacilities, FacilityReporters
from app.controllers.api import Cases, Deaths, Dhis2Queue, Test, ReportsThisWeek
from app.controllers.api2 import LocationsEndpoint, ReportersXLEndpoint
from app.controllers.api2 import CreateFacility, ReportForms, IndicatorHtml
from app.controllers.api2 import FacilitySMS, SendSMS, RequestDetails
from app.controllers.reporters_handler import Reporters
from app.controllers.users_handler import Users
from app.controllers.groups_handler import Groups
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
from app.controllers.polls_handler import Polls
from app.controllers.settings_handler import Settings
from app.controllers.forgotpass_handler import ForgotPass
from app.controllers.facilities_handler import Facilities
from app.controllers.downloads_handler import Downloads
from app.controllers.adminunits_handler import AdminUnits
from app.controllers.fsync_handler import FSync
from app.controllers.messagehistory_handler import MessageHistory
from app.controllers.facilityreports_handler import FacilityReports

URLS = (
    r'^/', Index,
    r'/smslog', SMSLog,
    r'/adminunits', AdminUnits,
    r'/downloads', Downloads,
    r'/reporters', Reporters,
    r'/approve', Approve,
    r'/facilities', Facilities,
    r'/auditlog', AuditLog,
    r'/settings', Settings,
    r'/fsync', FSync,
    r'/dashboard', Dashboard,
    r'/users', Users,
    r'/groups', Groups,
    r'/logout', Logout,
    r'/forgotpass', ForgotPass,
    r'/create', CreateFacility,
    r'/dataentry', DataEntry,
    r'/polling', Polls,
    r'/messagehistory/\+?(\w+)/?', MessageHistory,
    r'/facilityreports/(\w+)/?', FacilityReports,
    # Dispatcher2 URIs
    r'/requests', Requests,
    r'/completed', Completed,
    r'/failed', Failed,
    r'/search', Search,
    r'/ready', Ready,
    r'/appsettings', AppSettings,
    # API stuff follows
    r'/cases', Cases,  # cases flow
    r'/deaths', Deaths,  # deaths flow
    r'/dhis2queue', Dhis2Queue,  # queue reports in dispatcher2
    r'/test', Test,
    r'/api/v1/loc_children/(\d+)/?', LocationChildren,
    r'/api/v1/district_facilities/(\d+)/?', DistrictFacilities,
    r'/api/v1/facility_reporters/(\d+)/?', FacilityReporters,
    r'/api/v1/loc_facilities/(\d+)/?', LocationFacilities,
    r'/api/v1/location/(\d+)/?', Location,
    r'/api/v1/subcountylocations/(\d+)/?', SubcountyLocations,
    r'/api/v1/locations_endpoint/(\w+)/?', LocationsEndpoint,
    r'/api/v1/reporters_xlendpoint', ReportersXLEndpoint,
    r'/api/v1/reportsthisweek/(\w+)/?', ReportsThisWeek,
    r'/api/v1/reportforms/(\w+)/?', ReportForms,
    r'/api/v1/indicatorhtml/(\w+)/?', IndicatorHtml,
    r'/api/v1/facilitysms/(\d+)/?', FacilitySMS,
    r'/api/v1/sendsms', SendSMS,
    r'/api/v1/request_details/(\d+)/?', RequestDetails,
)
