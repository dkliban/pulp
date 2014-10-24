import logging
from gettext import gettext as _

from pulp.plugins.conduits.mixins import (ContentSourcesConduitException, StatusMixin,
    PublishReportMixin)
from pulp.server.content.sources.container import ContentContainer

from pulp.plugins.util.publish_step import Step
import threading
from pulp.common.plugins import reporting_constants
from pulp.server.exceptions import PulpCodedTaskException
from pulp.common import error_codes

logger = logging.getLogger(__name__)

class ContentSourcesConduit(StatusMixin, PublishReportMixin):
    """
    Used to communicate back into the Pulp server while content sources are
    are being cataloged. Instances of this call should *not* be cached between
    catalog refreshes. Each refresh task will be issued its own conduit
    instance that is scoped to that run alone.

    Instances of this class are thread-safe. Calls into this instance do not
    have to be coordinated for thread safety, the instance will take care of it itself.
    """

    def __init__(self, task_id):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str
        """
        StatusMixin.__init__(self, task_id, ContentSourcesConduitException)
        PublishReportMixin.__init__(self)


    def __str__(self):
        return 'ContentSourcesConduit'

class ContentSourcesRefreshStep(Step):
    """
    Content sources refresh step class that is responsible for refreshing all the content sources
    """

    def __init__(self, refresh_conduit, content_source_id=None):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """

        super(ContentSourcesRefreshStep, self).__init__(step_type=reporting_constants.REFRESH_STEP_CONTENT_SOURCE, status_conduit=refresh_conduit, non_halting_exceptions=[PulpCodedTaskException])

        self.container = ContentContainer()
        if content_source_id:
            self.sources = [self.container.sources[content_source_id]]
        else:
            self.sources = [source for name, source in self.container.sources.iteritems()]
        self.description = _("Refreshing content sources")

    def get_generator(self):
        return self.sources

    def process_main(self, item=None):
        if item:
            self.progress_description = item.descriptor['name']
            e = threading.Event()
            report = item.refresh(e)[0]
            self.details.append(report.dict())
            self.progress_details = self.details
            if not report.succeeded:
                raise PulpCodedTaskException(error_code=error_codes.PLP0031, id=report.source_id, url=report.url)

    def initialize(self):
        self.details = []

    def finalize(self):
        self.progress_details = self.details

    def _get_total(self):
        return len(self.sources)
