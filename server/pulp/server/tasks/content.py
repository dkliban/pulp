# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging

import celery

from pulp.common.error_codes import PLP0002, PLP0003, PLP0007
from pulp.common.tags import action_tag, resource_tag, RESOURCE_REPOSITORY_TYPE
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.content.sources.container import ContentContainer
from pulp.server.content.sources.steps import ContentSourcesConduit, ContentSourcesRefreshStep


logger = logging.getLogger(__name__)


@celery.task(base=Task)
def refresh_content_container():
    """
    Refresh the content catalog using available content sources.
    """
    conduit = ContentSourcesConduit('Refresh Content Container')
    step = ContentSourcesRefreshStep(conduit)
    step.process_lifecycle()
    errors = []
    '''
    result = None
    try:
        container = ContentContainer()
        e = threading.Event()
        reports = container.refresh(e, force=False)
        result = [r.dict() for r in reports]
    except Exception, e:
        errors.append(e)

    error = None
    if len(errors) > 0:
        error = PulpCodedException()
        error.child_exceptions = errors
    result = 'blah'
    return TaskResult(error=error, result=result)
    '''

@celery.task(base=Task)
def refresh_content_source(content_source_id):
    """
    Refresh the content catalog from a specific content source.
    """
    errors = []
    result = None
    try:
        container = ContentContainer()
        source = container.sources.get(content_source_id)
        reports = source.refresh()
        result = [r.dict() for r in reports]
        errors = None
    except Exception, e:
        errors.append(e)
    return TaskResult(error=errors, result=result)

