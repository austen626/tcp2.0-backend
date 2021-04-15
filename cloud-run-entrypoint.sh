#!/usr/bin/env bash

# Start the sql proxy
cloud_sql_proxy -instances=tcp-293717:us-east4:syn-tcp2-145-db-dev=tcp:3306 &
# Execute the rest of your ENTRYPOINT and CMD as expected.
exec "$@"
