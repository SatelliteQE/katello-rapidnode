#!/usr/bin/python
from subprocess import Popen
import paramiko
#from SSHLibrary import SSHClient

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
			raise exception, 'Invalid system type.'
	return config_file_contents

def get_credentials():
	#eventually need to make this configurable
	username = "root"
	password = "foobar"
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
	username, password = get_credentials()
	command = "cat /etc/katello/oauth_token-file"
	for results in paramiko_exec_command(parent, username, password, command):
		print results.strip()
	oauth_secret = results.strip()
	return oauth_secret

#def parent_gen_certs(parent):

#node-certs-generate --child-fqdn <host> --katello-user admin --katello-password admin --katello-activation-key node

#def child_regster(child):

#download cert
#subscription-manager

#def child_install(child):

#node-install --parent-fqdn <host> --pulp true --pulp-oauth-secret <secret> --puppet true --puppetca true --foreman-oauth-secret <secret> --register-in-foreman true -v


satellite_systems = read_config_file()
parent = satellite_systems[0][0]
parent_get_oauth_secret(parent)
