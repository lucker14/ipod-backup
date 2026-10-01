#!/bin/bash
"$(dirname "$0")/start_ipod_backup.sh"
RESULT=$?
echo
if [ "$RESULT" -eq 0 ]; then
    echo "Backup finished. Press Enter to close this window."
else
    echo "Backup did not finish successfully. Read the message above."
    echo "Press Enter to close this window."
fi
read -r
exit "$RESULT"
