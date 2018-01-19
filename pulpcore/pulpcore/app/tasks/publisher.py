from gettext import gettext as _
from logging import getLogger

from celery import shared_task
from django.db import transaction

from pulpcore.app import models
from pulpcore.tasking.services import storage
from pulpcore.tasking.tasks import UserFacingTask


log = getLogger(__name__)


