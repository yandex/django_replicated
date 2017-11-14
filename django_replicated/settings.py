# Cache backend name to store database state
REPLICATED_CACHE_BACKEND = None

# Timeout for dead databases alive check
REPLICATED_DATABASE_DOWNTIME = 60

# List of slave database aliases. Default database is always master
REPLICATED_DATABASE_SLAVES = []

# View name to state mapping
REPLICATED_VIEWS_OVERRIDES = {}

# Timeout for dead databases alive check for read only flag
REPLICATED_READ_ONLY_DOWNTIME = 20

# Number of retries before set read only flag
REPLICATED_READ_ONLY_TRIES = 1

# Cookie name for read-after-write workaround
REPLICATED_FORCE_MASTER_COOKIE_NAME = 'just_updated'

# Cookie life time in seconds
REPLICATED_FORCE_MASTER_COOKIE_MAX_AGE = 5

# Header name for forcing state switch
REPLICATED_FORCE_STATE_HEADER = 'HTTP_X_REPLICATED_STATE'

# Enable or disable state checking on writes
REPLICATED_CHECK_STATE_ON_WRITE = True

# Status codes on which set cookie for read-after-write workaround
REPLICATED_FORCE_MASTER_COOKIE_STATUS_CODES = (302, 303)


REPLICATED_MANAGE_ATOMIC_REQUESTS = False
