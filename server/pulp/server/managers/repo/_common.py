"""
Contains functionality common across all repository-related managers.

= Working Directories =
Working directories are as staging or temporary file storage by importers
and distributors. Each directory is unique to the repository and plugin
combination.

The directory structure for plugin working directories is as follows:
<pulp_storage>/working/<repo_id>/[importers|distributors]/<plugin_type_id>

For example, for importer "foo" and repository "bar":
/var/lib/pulp/working/bar/importers/foo

The rationale is to simplify cleanup on repository delete; the repository's
working directory is simply deleted.
"""

import logging
import os
import shutil

from pulp.common import dateutils
from pulp.server import config as pulp_config
from pulp.plugins.model import Repository, RelatedRepository, RepositoryGroup, \
    RelatedRepositoryGroup


logger = logging.getLogger(__name__)


def _ensure_tz_specified(time_stamp):
    """
    Check a datetime that came from the database to ensure it has a timezone specified in UTC
    Mongo doesn't include the TZ info so if no TZ is set this assumes UTC.

    :param time_stamp: a datetime object to ensure has UTC tzinfo specified
    :type time_stamp: datetime.datetime
    :return: The time_stamp with a timezone specified
    :rtype: datetime.datetime
    """
    if time_stamp:
        time_stamp = dateutils.to_utc_datetime(time_stamp, no_tz_equals_local_tz=False)

    return time_stamp


def to_transfer_repo(repo_data):
    """
    Converts the given database representation of a repository into a plugin
    repository transfer object, including any other fields that need to be
    included.

    @param repo_data: database representation of a repository
    @type  repo_data: dict

    @return: transfer object used in many plugin API calls
    @rtype:  pulp.plugins.model.Repository}
    """
    r = Repository(repo_data['id'], repo_data['display_name'], repo_data['description'],
                   repo_data['notes'], content_unit_counts=repo_data['content_unit_counts'],
                   last_unit_added=_ensure_tz_specified(repo_data.get('last_unit_added')),
                   last_unit_removed=_ensure_tz_specified(repo_data.get('last_unit_removed')))
    return r


def to_related_repo(repo_data, configs):
    """
    Converts the given database representation of a repository into a plugin's
    representation of a related repository. The list of configurations for
    the repository's plugins will be included in the returned type.

    @param repo_data: database representation of a repository
    @type  repo_data: dict

    @param configs: list of configurations for all relevant plugins on the repo
    @type  configs: list

    @return: transfer object used in many plugin API calls
    @rtype:  pulp.plugins.model.RelatedRepository
    """
    r = RelatedRepository(repo_data['id'], configs, repo_data['display_name'],
                          repo_data['description'], repo_data['notes'])
    return r


def repository_working_dir(repo_id, mkdir=True):
    """
    Determines the repository's working directory. Individual plugin working
    directories will be placed under this. If the mkdir argument is set to true,
    the directory will be created as part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    working_dir = os.path.join(_repo_working_dir(), repo_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def importer_working_dir(importer_type_id, repo_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository.
    If the mkdir argument is set to true, the directory will be created as
    part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk to the directory the importer can use for the
             given repository
    @rtype:  str
    """
    repo_working_dir = repository_working_dir(repo_id, mkdir)
    working_dir = os.path.join(repo_working_dir, 'importers', importer_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def distributor_working_dir(distributor_type_id, repo_id, mkdir=True):
    """
    Determines the working directory for a distributor to use for a repository.
    If the mkdir argument is set to true, the directory will be created as
    part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk to the directory the distributor can use for the
             given repository
    @rtype:  str
    """
    repo_working_dir = repository_working_dir(repo_id, mkdir)
    working_dir = os.path.join(repo_working_dir, 'distributors', distributor_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def to_transfer_repo_group(group_data):
    """
    Converts the given database representation of a repository group into a
    plugin transfer object.

    @param group_data: database representation of the group
    @type  group_data: dict

    @return: transfer object used in plugin calls
    @rtype:  pulp.plugins.model.RepositoryGroup
    """
    g = RepositoryGroup(group_data['id'], group_data['display_name'],
                        group_data['description'], group_data['notes'],
                        group_data['repo_ids'])
    return g


def to_related_repo_group(group_data, configs):
    """
    Converts the given database representation of a repository group into a
    plugin transfer object. The list of configurations for the requested
    group plugins are included in the returned type.

    @param group_data: database representation of the group
    @type  group_data: dict

    @param configs: list of plugin configurations to include
    @type  configs: list

    @return: transfer object used in plugin calls
    @rtype:  pulp.plugins.model.RelatedRepositoryGroup
    """
    g = RelatedRepositoryGroup(group_data['id'], configs, group_data['display_name'],
                               group_data['description'], group_data['notes'])
    return g


def repo_group_working_dir(group_id, mkdir=True):
    """
    Determines the repo group's working directory. Individual plugin working
    directories will be placed under this. If the mkdir argument is set to
    true, the directory will be created as part of this call.

    @param group_id: identifies the repo group
    @type  group_id: str

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    working_dir = os.path.join(_repo_group_working_dir(), group_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def group_importer_working_dir(importer_type_id, group_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository
    group. If the mkdir argument is set to true, the directory will be created
    as part of this call.

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    group_working_dir = repo_group_working_dir(group_id, mkdir)
    working_dir = os.path.join(group_working_dir, 'importers', importer_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def group_distributor_working_dir(distributor_type_id, group_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository
    group. If the mkdir argument is set to true, the directory will be created
    as part of this call.

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    group_working_dir = repo_group_working_dir(group_id, mkdir)
    working_dir = os.path.join(group_working_dir, 'distributors', distributor_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def _working_dir_root(worker_name):
    """
    Returns the path to the working directory of a worker

    :param worker_name:     Name of worker for which path is requested
    :type  name:            basestring
    """
    working_dir = pulp_config.config.get('server', 'working_directory')
    dir_root = os.path.join(working_dir, worker_name)
    return dir_root


def _repo_working_dir(worker_name):
    """
    Returns the path to the repos directory inside working directory

    :param worker_name:     Name of worker for which path is requested
    :type  name:            basestring
    """
    dir = os.path.join(_working_dir_root(worker_name), 'repos')
    return dir


def _repo_group_working_dir(worker_name):
    """
    Returns the path to the repo_groups directory inside working directory

    :param worker_name:     Name of worker for which path is requested
    :type  name:            basestring
    """
    dir = os.path.join(_working_dir_root(worker_name), 'repo_groups')
    return dir


def _create_working_directory(worker_name):
    """
    Creates a working directory inside the cache_directory as specified in /etc/pulp/server.conf
    default path for cache_directory is /var/cache/pulp

    :param worker_name:     Name of worker that uses the working directory created
    :type  name:            basestring
    """
    working_dir_root = _working_dir_root(worker_name)
    os.mkdir(working_dir_root)
    logger.debug('Cre %s', working_dir_root)


def _delete_working_directory(worker_name):
    """
    Deletes a working directory inside the cache_directory as specified in /etc/pulp/server.conf
    default path for cache_directory is /var/cache/pulp

    :param worker_name:     Name of worker that uses the working directory being deleted
    :type  name:            basestring
    """
    working_dir_root = _working_dir_root(worker_name)
    if os.path.exists(working_dir_root):
        shutil.rmtree(working_dir_root)
        logger.debug('Deleted %s', working_dir_root)