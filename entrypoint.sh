#!/bin/bash
set -e

THIS_DIR="$(cd "$(dirname "$0")"; pwd)"
source "$THIS_DIR/python_env/bin/activate"
export PYTHONPATH="$THISDIR:$PYTHONPATH"

if [[ -x "$THIS_DIR/pre-entry.sh" ]]; then
  echo "Sourcing pre-entry script" >&2
  source "$THIS_DIR/pre-entry.sh"
else
  echo "Skipping pre-entry script" >&2
fi

function pep8_ {
  pep8 "dockci"
}
function pylint_ {
  pylint --rcfile "$THIS_DIR/pylint.conf" "dockci"
}
function styletest {
  pep8_; pylint_
}
function doctest {
  py.test --doctest-modules -vvrxs "$THIS_DIR/dockci"
}
function ci {
  styletest; doctest
}
function _run {
  python -c "from dockci.logserve.$1 import run; run()"
}
function run-http {
  _run http
}
function run-consumer {
  _run consumer
}

case "$1" in
  styletest|doctest|ci|run-http|run-consumer) "$1" ;;
  *) "$@" ;;
esac
