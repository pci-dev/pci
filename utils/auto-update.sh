BR=$(git remote)/$(git branch --show-current)

git fetch 2>&1 | grep $BR && {
        git reset --hard $BR
        make reload.web2py
}
