#!/usr/bin/env sh
set -v

result=0

if [ $TEST = 'docs' ]; then
  pip3 install sphinx sphinxcontrib-openapi
  cd docs
  make html
  if [ $? -ne 0 ]; then
    result=1
  fi
else
  # flake8
  flake8 --config flake8.cfg || exit 1

  pulp-manager makemigrations pulp_file --noinput

  pulp-manager makemigrations pulp_app --noinput

  pulp-manager migrate auth --noinput
  pulp-manager migrate --noinput
  if [ $? -ne 0 ]; then
    result=1
  fi

  coverage run manage.py test pulpcore
  if [ $? -ne 0 ]; then
    result=1
  fi

  export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
  pulp-manager reset-admin-password --password admin
  pulp-manager runserver >> ~/django_runserver.log 2>&1 &
  rq worker -n 'resource_manager@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/resource_manager.log 2>&1 &
  rq worker -n 'reserved_resource_worker_1@%h' -w 'pulpcore.tasking.worker.PulpWorker' >> ~/reserved_worker-1.log 2>&1 &

  sleep 5

  py.test -v --color=yes --pyargs pulp_smash.tests.pulp3

  if [ $? -ne 0 ]; then
    result=1
    cat ~/django_runserver.log
    cat ~/resource_manager.log
    cat ~/reserved_worker-1.log
  fi

  if [ $result -eq 0 ]; then
    # upload coverage report to codecov
    codecov
  fi

fi

exit $result
