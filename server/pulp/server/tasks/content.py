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
from pulp.server.exceptions import PulpCodedException
from pulp.server.content.sources.container import ContentContainer
import threading


logger = logging.getLogger(__name__)


@celery.task(base=Task)
def refresh_content_container():
    """
    Refresh the content catalog using available content sources.
    """
    conduit = ContentSourceRefreshConduit('Refresh Content Container')
    step = ContentCatalogRefresher(conduit)
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
    '''
    error = None
    if len(errors) > 0:
        error = PulpCodedException()
        error.child_exceptions = errors
    result = 'blah'
    return TaskResult(error=error, result=result)


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









import sys

from pulp.plugins.conduits.mixins import (DistributorConduitException, RepoScratchPadMixin,
    RepoScratchpadReadMixin, DistributorScratchPadMixin,
    RepoGroupDistributorScratchPadMixin, StatusMixin,
    SingleRepoUnitsMixin, MultipleRepoUnitsMixin, PublishReportMixin)
import pulp.server.managers.factory as manager_factory
from pulp.common.plugins import reporting_constants
# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- classes -----------------------------------------------------------------

class ContentSourceRefreshConduit(StatusMixin, PublishReportMixin):
    """
    Used to communicate back into the Pulp server while a distributor is
    publishing a repo. Instances of this call should *not* be cached between
    repo publish runs. Each publish call will be issued its own conduit
    instance that is scoped to that run alone.

    Instances of this class are thread-safe. The distributor implementation is
    allowed to do whatever threading makes sense to optimize the publishing.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, task_id):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str
        """
        StatusMixin.__init__(self, task_id, DistributorConduitException)
        PublishReportMixin.__init__(self)


    def __str__(self):
        return 'ContentSourceRefreshConduit'

    # -- public ---------------------------------------------------------------



from gettext import gettext as _

import os

from pulp.plugins.util.publish_step import PluginStepIterativeProcessingMixin, Step


_LOG = logging.getLogger(__name__)


class ContentCatalogRefresher(Step):
    """
    Content source refresher class that is responsible for refreshing all the content sources
    """

    def __init__(self, refresh_conduit):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(ContentCatalogRefresher, self).__init__("Refresh Content Catalog",
                                           status_conduit=refresh_conduit)
        container = ContentContainer()

        for name, content_source in container.sources.iteritems():
            #import pydevd
            #pydevd.settrace('localhost', port=3011, stdoutToServer=True, stderrToServer=True)
            step = ContentSourceRefreshStep('Refresh %s' % name, content_source)
            self.add_child(step)


    def process_main(self):
        """
        Link the unit to the image content directory and the package_dir

        :param unit: The unit to process
        :type unit: pulp_docker.common.models.DockerImage
        """
        #do stuff ?? probably don't need to override
        #import pydevd
        #pydevd.settrace('localhost', port=3011, stdoutToServer=True, stderrToServer=True)

class ContentSourceRefreshStep(Step):

    def __init__(self, step_type, content_source):
        """
        TODO
        """
        self.content_source = content_source
        super(ContentSourceRefreshStep, self).__init__(step_type)

    def process_main(self):
        e = threading.Event()
        report = self.content_source.refresh(e)
        if not report[0].succeeded:
            self._record_failure()
            self.state = reporting_constants.STATE_FAILED
            raise PulpCodedException