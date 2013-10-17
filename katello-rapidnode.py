# -*- coding: utf-8 -*-
# katello-rapidnode.py 
# this allows users to quickly enable and configure nodes for katello/satellite6
#
# IMPORTANT NOTES:
# * This currently assumes you have 'node-installer' and 'v8' installed on child
#   system targets.  Later on maybe we'll assure this is installed.
# * There is very little error checking presently existing in here. Patches 
#   welcome.  Similarly, the code as a whole is probably pretty weak... :o


#!/usr/bin/env python
from subprocess import Popen
import paramiko
from termcolor import colored

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
			raise Exception, 'Installation requires exactly "1" parent node, please check your config file.'
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
# cat `/etc/katello/oauth_token-file`
	data = []
	username, password = get_credentials_parent()
	command = "cat /etc/katello/oauth_token-file"
	for results in paramiko_exec_command(parent, username, password, command):
		data.append(results.strip())
	oauth_secret = data[0]
	return oauth_secret

def parent_gen_certs(parent, child):
# node-certs-generate --child-fqdn <host> --katello-user admin --katello-password admin --katello-activation-key node
	data = []
	username, password = get_credentials_parent()
	command = "node-certs-generate --child-fqdn " + child + " --katello-user admin --katello-password admin --katello-activation-key node"
	print colored("Generating certs on parent...", 'blue', attrs=['bold'])
	for results in paramiko_exec_command(parent, username, password, command):
		print results.strip()

def child_register(parent, child):
# download cert
	data = []
	cmds = []
	username, password = get_credentials_children()
	parent_satcert = "http://" + parent +"/pub/candlepin-cert-consumer-latest.noarch.rpm"
	installrpm = "rpm -Uvh " + parent_satcert
# subscription-manager
	register = "subscription-manager register --org Katello_Infrastructure --activationkey node --force"
	cmds = installrpm, register
	print colored("Registering child to parent node...", 'blue', attrs=['bold'])
	for command in cmds:
		for results in paramiko_exec_command(child, username, password, command):
			print results.strip()

def child_install_node(parent, child):
	username, password = get_credentials_children()
	command = "node-install -v --parent-fqdn " + parent +" --pulp true --pulp-oauth-secret " \
			+ oauth_secret + " --puppet true --puppetca true --foreman-oauth-secret " \
			+ oauth_secret +  " --register-in-foreman true"
	print colored("Configuring child node...", 'blue', attrs=['bold'])
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

def child_nodeinstaller(child):
	data =[]
	username, password = get_credentials_children()
	command = "yum -y install node-installer v8"
	print colored("Installing node installer and v8...\n", 'blue', attrs=['bold'])
	for results in paramiko_exec_command(child, username, password, command):
		data.append(results)

#def parent_check_nodes(parent):
#TODO: basically run 
# `katello --user admin --password admin node list`
# to assure our nodes are online

def parent_get_org_environments():
# katello -u admin -p admin environment list --org "Katello Infrastructure" -g -d :
	data = []
	newdata = []
	record = []
	environments =  []
	username, password = get_credentials_parent()
	command = "katello -u admin -p admin environment list --org 'Katello Infrastructure' -g -d :"
	print colored("Determining environments in org on parent node...\n", 'blue', attrs=['bold'])
	for results in paramiko_exec_command(parent, username, password, command):
		data.append(results)
# Basically screen-scraping. What a hassle! is there a better way?
	data = data[0].split("\n")
	data = data[5:]
	data.pop(-1)
	for envdata in data:
		record = envdata.split(':')
		environments.append(record[1])
	return environments

def parent_populate_child_environments(parent, child):
# katello -u admin -p admin node add_environment --environment dev --org "Katello Infrastructure" --id 5
	data =[]
	environments = parent_get_org_environments()
        username, password = get_credentials_parent()
	print colored("Populating child node with environments...", 'blue', attrs=['bold'])
	for env in environments:
		command = "katello -u admin -p admin node add_environment --environment " \
		+ env + " --org \"Katello Infrastructure\" --name " + child
		print colored('[' + env + ']', 'cyan')
		for results in paramiko_exec_command(parent, username, password, command):
			print results.strip()

#def parent_sync_child(parent, child):
# TODO: Initiate syncing of child
# (waiting for stability assurance)

satellite_systems = read_config_file()
parent = satellite_systems[0][0]
oauth_secret = parent_get_oauth_secret(parent)

for child in satellite_systems[1]:
	print colored("Configuring node:", 'white', attrs=['bold', 'underline']) 
	print colored(child, 'cyan', attrs=['bold'])
	parent_gen_certs(parent, child)
	child_copy_repo(child)
	child_nodeinstaller(child)
	child_register(parent, child)
	child_install_node(parent, child)
	parent_populate_child_environments(parent, child)
