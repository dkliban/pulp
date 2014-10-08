#!/usr/bin/env python
import argparse

from fabric.api import settings, run

import os1_utils
import setup_utils


YUM_UPDATE_COMMAND = 'sudo yum -y update'
DEPENDENCY_LIST = [
    'puppet',
    'redhat-lsb'
]
PUPPET_MODULE_LIST = [
    'puppetlabs-stdlib',
    'puppetlabs-mongodb',
    'dprince-qpid',
    'jcline-pulp'
]
DEFAULT_DISTRIBUTIONS = [
    'el5',
    'el6',
    'el7',
    'fc19',
    'fc20'
]

description = 'Update one or more pulp images'
distributions_help = 'list of platforms to update (e.g. el5 el6 fc19); by default all platforms are updated'

parser = argparse.ArgumentParser(description=description)
parser.add_argument('--key-file', help='the path to the private key of the OS1 key pair', required=True)
parser.add_argument('--os-keyname', help='the name of the key pair in OpenStack to use', required=True)
parser.add_argument('--distributions', help=distributions_help, nargs='*')
parser.add_argument('--puppet-manifest', help='path to a puppet puppet manifest to apply')
args = parser.parse_args()

# Set the default platforms to all supported platforms
if not args.distributions:
    args.distributions = DEFAULT_DISTRIBUTIONS

os1 = os1_utils.OS1Manager()


def create_instances():
    instance_list = []
    # Boot the 'gold' image, update apply module, shutdown.
    pulp_images = os1.get_pulp_images(os1_utils.META_IMAGE_STATUS_VANILLA, args.distributions)
    for image in pulp_images:
        instance = os1.create_instance(image, image.name, os1_utils.DEFAULT_SEC_GROUP,
                                       'm1.small', args.os_keyname)
        instance_list.append(instance)

    os1.wait_for_active_instances(instance_list)
    return instance_list


def update(instance):
    host_string = os1.get_instance_user(instance) + '@' + os1.get_instance_floating_ip(instance)

    with settings(host_string=host_string, key_filename=args.key_file):
        # SELinux is broken on Fedora 20 release, so temporarily disable it.
        run('sudo setenforce 0', warn_only=True)
        run(YUM_UPDATE_COMMAND)

        for package in DEPENDENCY_LIST:
            run('sudo yum -y install ' + package)

        for module in PUPPET_MODULE_LIST:
            run('sudo puppet module install --force ' + module)

    if args.puppet_manifest:
        setup_utils.apply_puppet(host_string, args.key_file, args.puppet_manifest)

    os1.reboot_instance(instance)
    # Wait for the SSH server to come back online
    setup_utils.fabric_confirm_ssh_key(host_string, args.key_file)


def update_images():
    instance_list = create_instances()
    snapshot_list = []

    try:
        for instance in instance_list:
            update(instance)
            snapshot = os1.take_snapshot(instance, instance.name + '-SNAP')
            snapshot_list.append(snapshot)

        print 'Waiting for snapshots to finish... '
        os1.wait_for_snapshots(snapshot_list)

        # Clean up old snapshots if necessary
        #old_snapshots = os1.get_pulp_images(distributions=args.distributions)
        #for snap in old_snapshots:
        #    snap.delete()

        # Mark the images as prepped.
        meta = {os1_utils.META_IMAGE_STATUS_KEYWORD: os1_utils.META_IMAGE_STATUS_PREPPED}
        for snap in snapshot_list:
            os1.set_image_meta(snap, meta)
    except Exception:
        for snap in snapshot_list:
            snap.delete()
        raise
    finally:
        for instance in instance_list:
            os1.nova.servers.delete(instance)
        os1.release_free_floating_ips()

    return snapshot_list

snapshots = update_images()

print 'New snapshots: ' + repr(snapshots)
