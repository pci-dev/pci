#!/bin/bash

# Example : ./install-texlive.sh EB3

APP=$1
if [ -z $APP ]; then
    echo "APP name missing"
    exit
fi

if [ ! -d "$HOME/texlive" ]; then
    cd /tmp
    curl -L -o install-tl-unx.tar.gz https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
    zcat < install-tl-unx.tar.gz | tar xf -
    cd `ls | grep install-tl-2 | tail -1`
    perl ./install-tl --no-interaction --texdir=$HOME/texlive
else
    echo "$HOME/texlive already exists"
fi

cd $HOME

PDFLATEX_BIN=$PWD/texlive/bin/x86_64-linux/pdflatex
CONFIG_FILE=$PWD/sites/$APP/private/appconfig.ini

echo -e "\n[latex]\npdflatex = $PDFLATEX_BIN" >> $CONFIG_FILE
