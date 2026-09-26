#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 start_backup.py
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
