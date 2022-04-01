#!/usr/bin/env zsh
cd /mnt/e/github_repos && \
for REPO in $(cat ~/devel/python/tcc/output/selected_repos)
do
  DATE=$(date "+%Y-%m-%d %H:%M:%S")
  OWNER_REPO=$(echo $REPO | sed -n 's|/|____|p')
  echo -ne "$DATE | Read: $REPO\033[0K\r"
  if [ -s ~/devel/python/tcc/loggings-per-repo/$OWNER_REPO.loggings ]
  then
    echo -ne "$DATE | Skip: $REPO <<~~~~~~~~\033[0K\r"
  else
    pcre2grep -H -M -n -r -s -u --include='\.py$' -f ~/devel/python/tcc/logging_patterns \
        $REPO > ~/devel/python/tcc/loggings-per-repo/$OWNER_REPO.loggings
    RC=$?
    if [ $RC != 0 ]
    then
      echo -ne "$DATE | ERROR($RC): $REPO <<########\033[0K\r"
      echo "$REPO" >> ~/devel/python/tcc/output/failed-to-pcre2grep.repos
    else
      echo -ne "$DATE | Done: $REPO <<-- $(date "+%H:%M:%S")\033[0K\r"
    fi
  fi
  echo
done