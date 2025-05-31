#!/bin/bash
LOGFILE=/home/pi/gpp_check.log

# Log the check
echo "$(date): Checking if gpp.py is running" >> $LOGFILE

# Check if gpp.py is running
if ! /usr/bin/pgrep -f "gpp.py" > /dev/null
then
    # Log the restart attempt
    echo "$(date): gpp.py not running. Starting it now..." >> $LOGFILE
    # If not running, execute the start command
    /usr/bin/sudo -u pi DISPLAY=:0 /home/pi/GP/start_gpp.sh >> $LOGFILE 2>&1
    echo "$(date): start_gpp.sh executed." >> $LOGFILE
else
    echo "$(date): gpp.py is already running." >> $LOGFILE
fi
