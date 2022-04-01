#!/usr/bin/zsh

if [ $# != 1 ]
then
  echo "Syntax: $0 <file_path>"
  exit 1
fi

if [ -s $1 ]
then
  FILE_ENC=$(file -b $1)
  if [[ ! $FILE_ENC =~ "ASCII" ]] && [[ $FILE_ENC =~ "BOM" ]]
  then
    cp $1 $1.bkp
    sed -i '1s/^\xEF\xBB\xBF//' $1
    file -b $1
  elif [[ ! $FILE_ENC =~ "ASCII" ]] && [[  $FILE_ENC =~ "ISO-8859" ]]
  then
    cp $1 $1.bkp
    iconv -f ISO-8859-1 -t ASCII//TRANSLIT -o $1 $1
  elif [[ $FILE_ENC == "data" ]]
  then
    date "+%Y-%m-%d %H:%M:%S | Not a valid text file | Encoding: $FILE_ENC | Lines: $(wc -l $1)"
    exit 2
  else
    date "+%Y-%m-%d %H:%M:%S | File not converted | Encoding: $FILE_ENC | Lines: $(wc -l $1)"
    # exit 2
  fi
else
  date "+%Y-%m-%d %H:%M:%S | Not a valid text file w/ lenght > 0 | $1"
  exit 1
fi
exit 0
