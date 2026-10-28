UNIT_OFFICER = "unit_officer"
UNIT_SUPERVISOR = "unit_supervisor"
REGIONAL_OFFICER = "regional_officer"
MANAGEMENT = "management"
COMPETENT_AUTHORITY = "competent_authority"
ADMIN = "admin"
AUDITOR = "auditor"

# People who signed up themselves. "new" has not chosen what they are yet; "pending" waits for an administrator.
NEW = "new"
PENDING = "pending"
COMPLAINANT = "complainant"
INSTITUTION_REP = "institution_rep"
PUBLIC_ROLES = (COMPLAINANT, INSTITUTION_REP)
# Staff roles a person may ask for (an administrator approves; "admin" is never self-service).
REQUESTABLE_STAFF = (UNIT_OFFICER, UNIT_SUPERVISOR, REGIONAL_OFFICER, MANAGEMENT, COMPETENT_AUTHORITY, AUDITOR)

ALL_ROLES = (
    UNIT_OFFICER, UNIT_SUPERVISOR, REGIONAL_OFFICER,
    MANAGEMENT, COMPETENT_AUTHORITY, ADMIN, AUDITOR,
)
OFFICER = (UNIT_OFFICER, UNIT_SUPERVISOR, REGIONAL_OFFICER)  # "O" in BACKEND_PLAN section 5
