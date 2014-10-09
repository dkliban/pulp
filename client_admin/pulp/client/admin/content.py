from gettext import gettext as _
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption


def initialize(context):
    """
    Initialize the *content* section.
    :param context: The client context.
    :type context: pulp.client.extensions.core.ClientContext
    """
    main = MainSection(context)
    context.cli.add_section(main)


class MainSection(PulpCliSection):
    """
    The *content* main section.
    :ivar context: The client context.
    :type context: pulp.client.extensions.core.ClientContext
    """

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(MainSection, self).__init__('content', _('manage content'))
        self.add_subsection(SourcesSection(context))


class SourcesSection(PulpCliSection):

    def __init__(self, context):
        """
        :param context: The client context.
        :type context: pulp.client.extensions.core.ClientContext
        """
        super(SourcesSection, self).__init__('sources', _('manage content sources'))
        self.context = context
        self.add_command(PulpCliCommand('list', _('list sources'), self._list))

    def _list(self):
        """
        List content sources.
        """
        self.context.prompt.render_title(_('Content Sources'))
        sources = self.context.server.content_source.get_all()
        self.context.prompt.render_document_list(sources)
