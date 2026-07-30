#!/usr/bin/with-contenv bashio
export NOTIFY_SERVICE=$(bashio::config 'notify_service')
export MIN_CONFIDENCE=$(bashio::config 'min_confidence')
export CYCLE_DELAY_SECONDS=$(bashio::config 'cycle_delay_seconds')
python3 /ai_autonomy_steward.py
