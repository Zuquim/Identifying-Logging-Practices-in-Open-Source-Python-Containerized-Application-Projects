#!/usr/bin/env zsh

if [ $# != 1 ]
then
  echo "\nSyntax: $0 <egrep_filter>"
  exit 1
fi

# cd ~/devel/python/tcc
# REPOS=$(egrep -i "$1" radon_fault.list)
# awk 'BEGIN {FS="/"}; {print $1 "/" $2}' radon-fault.list | uniq | wc -l
# for FIL in $(cat radon-fault.list); do wc -l "/mnt/e/github_repos/$FIL"; done

cd /mnt/e/github_repos && \
for REPO in $(egrep -i "$1" ~/devel/python/tcc/radon_fault.list | sort -r)
do DATE=$(date "+%Y-%m-%d %H:%M:%S")
  OWNER_REPO=$(echo $REPO | sed -n 's|/|.|p')
  echo -ne "$DATE | Calc: $REPO\033[0K\r"
  if [ -s ~/devel/python/tcc/radon_raw_json/$OWNER_REPO.json ]
  then echo -ne "$DATE | Skip: $REPO <<~~~~~~~~"
  else radon raw -s -j -O ~/devel/python/tcc/radon_raw_json/$OWNER_REPO.json $REPO \
      >> /tmp/radon-$OWNER_REPO-stdout.txt 2>> /tmp/radon-$OWNER_REPO-stderr.txt
    echo -ne "$DATE | Done: $REPO <<-- $(date "+%H:%M:%S")"
  fi
  echo
done
