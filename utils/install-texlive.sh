#!/bin/bash

# Example : ./install-texlive.sh EB3

APP=$1
if [ -z $APP ]; then
    echo "APP name missing"
    exit
fi

if [ -d "$HOME/texlive" ]; then
    echo "$HOME/texlive already exists"
    exit 1
fi

    cd /tmp
    curl -L -o install-tl-unx.tar.gz https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
    zcat < install-tl-unx.tar.gz | tar xf -
    cd `ls | grep install-tl-2 | tail -1`
    perl ./install-tl --no-interaction --texdir=$HOME/texlive || {
        echo "error installing texlive"
        exit 2
    }

cd $HOME

LATEX_COMPILER_BIN=$PWD/texlive/bin/x86_64-linux/lualatex
CONFIG_FILE=$PWD/sites/$APP/private/appconfig.ini

echo -e "\n[latex]\ncompiler = $LATEX_COMPILER_BIN" >> $CONFIG_FILE
