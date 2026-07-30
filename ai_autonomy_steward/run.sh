#!/usr/bin/with-contenv bashio
export MIN_CONFIDENCE=$(bashio::config 'min_confidence')
python3 /ai_autonomy_steward.py
