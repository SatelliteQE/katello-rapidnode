# katello-rapidnode.py 
# this allows users to quickly enable and configure nodes for katello/satellite6
#
# IMPORTANT NOTES:
# * This currently assumes you have 'node-installer' and 'v8' installed on child
#   system targets.  Later on maybe we'll assure this is installed.
# * There is very little error checking presently existing in here. Patches 
#   welcome.  Similarly, the code as a whole is probably pretty weak... :o


#!/usr/bin/python
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

def get_credentials():
# eventually need to make this configurable
# note that we're currently ass-u-me-ing parent and children
# have the same password
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
	data = []
	username, password = get_credentials()
	command = "cat /etc/katello/oauth_token-file"
	for results in paramiko_exec_command(parent, username, password, command):
		data.append(results.strip())
	oauth_secret = data[0]
	return oauth_secret

def parent_gen_certs(parent, child):
# node-certs-generate --child-fqdn <host> --katello-user admin --katello-password admin --katello-activation-key node
	data = []
	username, password = get_credentials()
	command = "node-certs-generate --child-fqdn " + child + " --katello-user admin --katello-password admin --katello-activation-key node" 
	print colored("Generating certs on parent...", 'blue', attrs=['bold'])
	for results in paramiko_exec_command(parent, username, password, command):
		print results.strip()
	
def child_register(parent, child):
# download cert
	data = []
	cmds = []
	username, password = get_credentials()
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
	username, password = get_credentials()
	command = "node-install -v --parent-fqdn " + parent +" --pulp true --pulp-oauth-secret " \
			+ oauth_secret + " --puppet true --puppetca true --foreman-oauth-secret " \
			+ oauth_secret +  " --register-in-foreman true"
	print colored("Configuring child node...", 'blue', attrs=['bold'])
	for results in paramiko_exec_command(child, username, password, command):
		print results.strip()

#def parent_check_nodes(parent):
#TODO: basically run 
# `katello --user admin --password admin node list`
# to assure our nodes are online

satellite_systems = read_config_file()
parent = satellite_systems[0][0]
oauth_secret = parent_get_oauth_secret(parent)

for child in satellite_systems[1]:
	print colored("Configuring node:", 'white', attrs=['bold', 'underline']) 
	print colored(child, 'cyan', attrs=['bold'])
	parent_gen_certs(parent, child)
	child_register(parent, child)
	child_install_node(parent, child)

