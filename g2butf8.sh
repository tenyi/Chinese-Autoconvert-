#!/bin/sh
files=`ls -l *.ass | awk '{print $9}'`
for i in ${files}; do
  python g2butf8.py ${i}
done
echo "DONE!!"
