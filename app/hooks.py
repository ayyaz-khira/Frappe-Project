app_name = "app"
app_title = "App"
app_publisher = "Ayyaz Khira"
app_description = "App for Registration"
app_email = "app@outlook.com"
app_license = "mit"


fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "=", "User"],
            ["fieldname", "=", "organization"]
        ]
    }
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "app",
# 		"logo": "/assets/app/logo.png",
# 		"title": "App",
# 		"route": "/app",
# 		"has_permission": "app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/app/css/app.css"
# app_include_js = "/assets/app/js/app.js"

# include js, css files in header of web template
# web_include_css = "/assets/app/css/app.css"
# web_include_js = "/assets/app/js/app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "app/public/icons.svg"

# Home Pages
# ----------

# website user home page (by Role)
role_home_page = {
    "Organization Admin": "dashboard",
    "System Manager": "dashboard"
}


# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "app.utils.jinja_methods",
# 	"filters": "app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "app.install.before_install"
# after_install = "app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "app.uninstall.before_uninstall"
# after_uninstall = "app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "app.utils.before_app_install"
# after_app_install = "app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "app.utils.before_app_uninstall"
# after_app_uninstall = "app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"User": "app.api.get_user_permission_query",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User Registration": {
        "on_update": "app.api.handle_registration_approval", # Removed "app.app"
        "after_save": "app.api.handle_registration_approval"
    }
}



website_route_rules=[

    {
        "from_route":"/home","to_route":"dashboard"
    }
]




on_login = "app.api.redirect_after_login"
# Templates are automatically picked up due to standard naming (password_reset.html, new_user.html)


 
 # Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"app.tasks.all"
# 	],
# 	"daily": [
# 		"app.tasks.daily"
# 	],
# 	"hourly": [
# 		"app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["app.utils.before_request"]
# after_request = ["app.utils.after_request"]

# Job Events
# ----------
# before_job = ["app.utils.before_job"]
# after_job = ["app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

