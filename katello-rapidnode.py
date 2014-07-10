# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 expandtab ai
# katello-rapidnode.py
# this allows users to quickly enable and configure capsules for katello/satellite6
#
# IMPORTANT NOTES:
# * There is very little error checking presently existing in here. Patches
#   welcome.  Similarly, the code as a whole is probably pretty weak... :o


#!/usr/bin/env python
from subprocess import Popen
import sys
try:
    import paramiko
except ImportError, e:
    print "Please install paramiko."
    sys.exit(-1)

try:
    from termcolor import colored
except ImportError, e:
    print "Please install termcolor module."
    sys.exit(-1)

def read_config_file():
    parent = []
    child = []
    config_file_contents = [parent, child]
    config_file = open('katello-rapidnode-config.txt')
    for line in config_file:
        line = line.rstrip()
        system_type = line.split(':')
        if system_type[0] == "p":
            config_file_contents[0].append(system_type[1])
        elif system_type[0] == "c":
            config_file_contents[1].append(system_type[1])
        else:
            raise Exception, 'Invalid system type.'
    if len(config_file_contents[0]) != 1:
            raise Exception, 'Installation requires exactly "1" parent instance, please check your config file.'
    return config_file_contents

def get_credentials_parent():
    credentials_file = open('katello-rapidnode-credentials.txt')
    for line in credentials_file:
        line = line.rstrip()
        username, password = line.split(':')
    return (username, password)

def get_credentials_children():
    credentials_file = open('katello-rapidnode-credentials-children.txt')
    for line in credentials_file:
        line = line.rstrip()
        username, password = line.split(':')
    return (username, password)

def paramiko_exec_command(system, username, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(system, username=username, password=password)
    stdin, stdout, stderr = ssh.exec_command(command)
    ret1 = stdout.read()
    ret2 = stderr.read()
    ssh.close()
    return ret1, ret2

def parent_get_oauth_secret(parent):
    oauth_data = []
    username, password = get_credentials_parent()
    #print colored("Grabbing oauth credentials from parent...", 'blue', attrs=['bold'])
    # surely there are better ways to do this...
    scrape_commands = ["grep oauth_consumer_key /etc/foreman/settings.yaml |sed 's/^:oauth_consumer_key: //'",
        "grep oauth_consumer_secret /etc/foreman/settings.yaml |sed 's/^:oauth_consumer_secret: //'",
        "grep oauth_secret /etc/pulp/server.conf |grep -v '#'| sed 's/^oauth_secret: //'"]
    for scrape in scrape_commands:
        data = []
        command = scrape
        for results in paramiko_exec_command(parent, username, password, command):
            data.append(results.strip())
        oauth_data.append(data[0])
    return oauth_data

def parent_gen_cert(parent, child):
    # capsule-certs-generate --capsule-fqdn <host> --certs-tar "<host>-certs.tar"
    data = []
    username, password = get_credentials_parent()
    command = "capsule-certs-generate -v --capsule-fqdn " + child + " --certs-tar " + child + "-certs.tar"
    print colored("Generating certs on parent...", 'blue', attrs=['bold'])
    for results in paramiko_exec_command(parent, username, password, command):
        print results.strip()

# Do these two until I figure out a convenient way to do ssh-keys
# 1)
def parent_copy_cert_local(parent, child):
    certs_file = child + "-certs.tar"
    port = 22
    username, password = get_credentials_parent()
    transport = paramiko.Transport((parent, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print colored("Retrieving certs file from parent...", 'blue', attrs=['bold'])
    sftp.get(certs_file, certs_file)
    sftp.close()

# 2)
def child_copy_cert(child):
    certs_file = child + "-certs.tar"
    port = 22
    username, password = get_credentials_children()
    transport = paramiko.Transport((child, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print colored("Pushing certs to child...", 'blue', attrs=['bold'])
    sftp.put(certs_file, certs_file)
    sftp.close()

def child_register(parent, child):
    # download cert
    data = []
    cmds = []
    username, password = get_credentials_children()
    parent_satcert = "http://" + parent +"/pub/katello-ca-consumer-latest.noarch.rpm"
    installrpm = "rpm -Uvh " + parent_satcert
    # subscription-manager
    # Note the hard-coded org and environment/content view.  This (sh|c)ould probably be
    # parameterized. Also note it means you need to have your environment set up
    # like this in order to use the script w/o modification...
    register = "subscription-manager register --username admin --password changeme \
        --org ACME_Corporation --environment 'dev/mycv'  --auto-attach --force"
    cmds = installrpm, register
    print colored("Registering/subscribing child to parent...", 'blue', attrs=['bold'])
    for command in cmds:
        for results in paramiko_exec_command(child, username, password, command):
            print results.strip()

def child_capsule_init(parent, child):
    username, password = get_credentials_children()
    foreman_oauth_key, foreman_oauth_secret, pulp_oauth_secret = parent_get_oauth_secret(parent)
    certs_tar = child + "-certs.tar"
    command = "capsule-installer -v --certs-tar " + certs_tar + " --parent-fqdn " \
        + parent +" --pulp true --pulp-oauth-secret " \
        + pulp_oauth_secret + " --puppet true --puppetca true --foreman-oauth-secret " \
        + foreman_oauth_secret +  " --foreman-oauth-key " \
        + foreman_oauth_key + " --register-in-foreman true"
    print colored("Configuring child capsule (this may take a while)...", 'blue', attrs=['bold'])
    for results in paramiko_exec_command(child, username, password, command):
        print results.strip()

def child_copy_repo(child):
    # If there are any various repos you need to upload to remote host,
    # Put them in 'myrepofile.repo'
    repo_file = 'myrepofile.repo'
    remote_repo_file = '/etc/yum.repos.d/' + repo_file
    port = 22
    username, password = get_credentials_children()
    transport = paramiko.Transport((child, port))
    transport.connect(username=username, password=password)
    remote_repo_file = '/etc/yum.repos.d/' + repo_file
    sftp = paramiko.SFTPClient.from_transport(transport)
    print colored("Copying applicable repo file to child...", 'blue', attrs=['bold'])
    sftp.put(repo_file, remote_repo_file)
    sftp.close()

def child_capsule_installer(child):
    # Pretty self-explanatory. Be sure you have a source repo for 'katello-installer'
    # of course...
    data = []
    username, password = get_credentials_children()
    command = "yum -y install katello-installer"
    print colored("Installing capsule-installer...\n", 'blue', attrs=['bold'])
    for results in paramiko_exec_command(child, username, password, command):
        data.append(results)

def child_disable_selinux(child):
    #This is a temporary thing only.
    data = []
    username, password = get_credentials_children()
    command = "setenforce 0"
    print colored("Disabling selinux on child...\n", 'blue', attrs=['bold'])
    for results in paramiko_exec_command(child, username, password, command):
        data.append(results)

#def parent_check_nodes(parent):
#TODO: basically run
# `hammer capsule list`
# to assure our nodes are online

# Get orgs available to capsules.
# Interesting note: 'hammer environment list' and
# 'hammer capsule content available-lifecycle-environments' do not return
# the same data.  This had me baffled for a while.
def parent_get_org_environments(capsule_id):
    data = []
    record = []
    environments = []
    username, password = get_credentials_parent()
    command = "hammer --output csv capsule content available-lifecycle-environments --id " + capsule_id
    for results in paramiko_exec_command(parent, username, password, command):
        data.append(results)
    # Basically screen-scraping. What a hassle! is there a better way?
    environments = data[0].split("\n")
    environments.pop()
    environments.pop(0)
    return environments

# Get all capsules tied to parent instance
def parent_get_capsules():
    data = []
    record = []
    capsule_ids = []
    capsule_names = []
    username, password = get_credentials_parent()
    command = "hammer --output csv capsule list"
    for results in paramiko_exec_command(parent, username, password, command):
        data.append(results)
    # Once again...
    capsules = data[0].split("\n")
    capsules.pop()
    capsules.pop(0)
    return capsules

def populate_capsules(parent, child):
    # For now this needs to be run after ALL capsules have been created.
    # This is because all content pushes are currently done via capsule id.
    # It is very difficult to associate a capsule id with the capsule name
    # we have provided at the beginning and have it make sense visually.
    #
    # IOW we can only sync by 'id', not by the 'hostname' users provide in
    # the config settings.
    #
    # If there exists a way to simply perform all the 'capsule content'
    # functions via capsule name vs id, this can be easily remedied later.
    data = []
    print colored("Determining all capsules...\n", 'blue', attrs=['bold'])
    capsules = parent_get_capsules()
    username, password = get_credentials_parent()
    print colored("Populating child capsule with environments...", 'blue', attrs=['bold'])
    for cap in capsules:
        capsule_id, capsule_name, capsule_url = cap.split(",")
        print colored("Populating capsule:", 'white', attrs=['bold', 'underline'])
        print colored(capsule_name, 'cyan', attrs=['bold'])
        # Don't try to do anything to default capsule
        if capsule_id != "1":
            print colored("Determining applicable environments for capsule...\n", 'blue', attrs=['bold'])
            environments = parent_get_org_environments(capsule_id)
            for env in environments:
                env_id, env_name, env_org = env.split(",")
                print colored('[' + env_org + '/' + env_name + ']', 'cyan')
                command = "hammer capsule content add-lifecycle-environment --environment-id " \
                    + env_id + " --id " + capsule_id
                for results in paramiko_exec_command(parent, username, password, command):
                    print results.strip()
            # Using async below detaches us sooner and allows kickoff of another capsule
            # But obviously we lose traceability from the script side of things. I think it's
            # ok, since we can always tail log files on capsules.
            sync_command = "hammer capsule content synchronize --async --id " + capsule_id
            for results in paramiko_exec_command(parent, username, password, sync_command):
                print results.strip()

satellite_systems = read_config_file()
parent = satellite_systems[0][0]
for child in satellite_systems[1]:
    print colored("Configuring capsule:", 'white', attrs=['bold', 'underline'])
    print colored(child, 'cyan', attrs=['bold'])
    parent_gen_cert(parent, child)
    child_copy_repo(child)
    child_register(parent, child)
    child_disable_selinux(child)
    parent_copy_cert_local(parent, child)
    child_copy_cert(child)
    child_capsule_installer(child)
    child_capsule_init(parent, child)

# After configuration is complete, populate environments (and eventually content)
# for ALL capsules
populate_capsules(parent, child)
