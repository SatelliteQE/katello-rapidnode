"""
Allows users to quickly enable and configure capsules for katello/satellite6

IMPORTANT NOTES:
We now have (some) error-checking! Most steps -- at least those that
are more prone to breaking due to misconfiguration -- will exit out rather
than run on blindly and waste time.

"""
from __future__ import print_function
from configparser import ConfigParser
from locale import getdefaultlocale
from termcolor import colored
import paramiko
import sys

CONFIG = ConfigParser()
CONFIG.read('katello_rapidnode.ini')
PARENT = CONFIG['servers']['parent']


def main():
    """Set up one or more capsules"""
    for child in CONFIG['servers']['children'].split(','):
        print(colored(
            "Configuring capsule:", 'white', attrs=['bold', 'underline']
        ))
        print(colored(child, 'cyan', attrs=['bold']))
        parent_gen_cert(PARENT, child)
        child_register(PARENT, child)
        parent_copy_cert_local(PARENT, child)
        child_copy_cert(child)
        child_capsule_installer(child)
        child_capsule_init(PARENT, child)
    # After configuration is complete, populate environments
    # (and eventually content) for ALL capsules
    populate_capsules(parent=PARENT)


def get_credentials_parent():
    """Gets credentials for the parent server"""
    return tuple(CONFIG['credentials']['parent'].split(':'))


def get_credentials_children():
    """Gets credentials for the child server(s)"""
    return tuple(CONFIG['credentials']['children'].split(':'))


def cmd_debug(cmd):
    """If enabled in config file, this outputs the raw commands being
    passed to servers, for debugging purposes.
    """
    if CONFIG['mainprefs']['show_raw_command'] == '1':
        print(colored(cmd, 'white', 'on_cyan', attrs=['bold']))


def paramiko_exec_command(system, username, password, command):
    """Executes command using paramiko"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(system, username=username, password=password)
    dummy, stdout, stderr = ssh.exec_command(command)
    miko_stdout = stdout.read()
    miko_stderr = stderr.read()
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()
    return miko_stdout, miko_stderr, exit_status


def remote_cmd(host, username, password, command, halt_on_fail=True):
    """Performs the actual paramiko goo and returns appropriate exit code"""
    stdout, stderr, exit_code = paramiko_exec_command(
        host, username, password, command)
    print(colored("stdout:\n", attrs=['underline']), stdout)
    print(colored("stderr:\n", attrs=['underline']), stderr)
    if exit_code != 0:
        print("Remote system returned exit code of: ", exit_code)
        if not halt_on_fail:
            print(colored(
                'WARNING: A non zero exit code was returned, but ignoring.',
                'yellow'
            ))
        else:
            print(colored(
                'ERROR: A non-zero exit code was returned; '
                'bailing...\nPlease review console messages above and/or '
                'remote server logs.', 'red', attrs=['bold']
            ))
            sys.exit(1)


def parent_get_oauth_secret(parent):
    """Gets parent oauth secret"""
    # surely there are better ways to do this...
    print(colored(
        'Grabbing oauth credentials from parent...', 'blue', attrs=['bold']
    ))
    username, password = get_credentials_parent()
    return [
        # This one, too, is not immediately compatible with the new function
        # and I'm not exactly sure why.  We'll update it later.
        paramiko_exec_command(parent, username, password, command)[0].strip()
        for command
        in (
            # (line-too-long) pylint:disable=C0301
            "grep oauth_consumer_key /etc/foreman/settings.yaml |sed 's/^:oauth_consumer_key: //'",  # noqa
            "grep oauth_consumer_secret /etc/foreman/settings.yaml |sed 's/^:oauth_consumer_secret: //'",  # noqa
            "grep oauth_secret /etc/pulp/server.conf |grep -v '#'| sed 's/^oauth_secret: //'",  # noqa
        )
    ]


def parent_gen_cert(parent, child):
    """Generates cert

    capsule-certs-generate --capsule-fqdn <host> --certs-tar "<host>-certs.tar"
    """
    username, password = get_credentials_parent()
    command = ("capsule-certs-generate -v --capsule-fqdn {0} --certs-tar {0}"
               "-certs.tar").format(child)
    cmd_debug(command)
    print(colored("Generating certs on parent...", 'blue', attrs=['bold']))
    remote_cmd(parent, username, password, command)


# FIXME: Do this until a convenient way is figured out to do ssh-keys
def parent_copy_cert_local(parent, child):
    """Copies parent cert"""
    certs_file = child + "-certs.tar"
    port = 22
    username, password = get_credentials_parent()
    transport = paramiko.Transport((parent, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(colored("Retrieving certs file from parent...", 'blue',
                  attrs=['bold']))
    sftp.get(certs_file, certs_file)
    sftp.close()


# FIXME: Do this until a convenient way is figured out to do ssh-keys
def child_copy_cert(child):
    """Copies child cert"""
    certs_file = child + "-certs.tar"
    port = 22
    username, password = get_credentials_children()
    transport = paramiko.Transport((child, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    print(colored("Pushing certs to child...", 'blue', attrs=['bold']))
    sftp.put(certs_file, certs_file)
    sftp.close()


def child_register(parent, child):
    """Registers the child"""
    username, password = get_credentials_children()
    commands = []
    commands.append(
        'rpm --force -Uvh http://{0}/pub/katello-ca-consumer-latest.noarch.rpm'
        .format(parent)
    )
    if CONFIG.get('mainprefs', 'contentview', fallback=None) is not None:
        commands.append(
            'subscription-manager register --username admin --auto-attach '
            '--force --password {0} --org {1} --environment {2} '
            .format(
                CONFIG['credentials']['adminpassword'],
                CONFIG['mainprefs']['orgname'],
                CONFIG['mainprefs']['contentview'],
            )
        )
    if CONFIG.get('mainprefs', 'activationkey', fallback=None) is not None:
        commands.append(
            'subscription-manager register --org={0} '
            '--activationkey={1} --force'
            .format(
                CONFIG['mainprefs']['orgname'],
                CONFIG['mainprefs']['activationkey'],
            )
        )
    print(colored(
        'Registering/subscribing child to parent...', 'blue', attrs=['bold']
    ))
    for command in commands:
        cmd_debug(command)
        remote_cmd(child, username, password, command)


def child_capsule_init(parent, child):
    """Initialize child capsule"""
    username, password = get_credentials_children()
    foreman_oauth_key, foreman_oauth_secret, pulp_oauth_secret = (
        parent_get_oauth_secret(parent))
    certs_tar = child + "-certs.tar"
    parent_base_url = "https://" + parent
    command = ("satellite-installer --scenario capsule -v "
               "--capsule-certs-tar {0} "
               "--capsule-parent-fqdn {1} "
               "--foreman-proxy-register-in-foreman true "
               "--foreman-proxy-foreman-base-url {3} "
               "--foreman-proxy-trusted-hosts {2} "
               "--foreman-proxy-trusted-hosts {1} "
               "--capsule-pulp-oauth-secret {4} "
               "--foreman-proxy-oauth-consumer-secret {5} "
               "--foreman-proxy-oauth-consumer-key {6} "
               ).format(certs_tar, parent, child, parent_base_url,
                        pulp_oauth_secret,
                        foreman_oauth_secret, foreman_oauth_key)
    cmd_debug(command)
    print(colored("Configuring child capsule (this may take a while)...",
                  'blue', attrs=['bold']))
    remote_cmd(child, username, password, command)


def child_capsule_installer(child):
    """ Installer for child capsule.

    Note: Be sure you have a source repo for install
    """
    username, password = get_credentials_children()
    command = "yum -y install satellite-installer"
    cmd_debug(command)
    print(colored("Installing capsule...\n", 'blue', attrs=['bold']))
    remote_cmd(child, username, password, command)


def child_disable_selinux(child):
    """Disable child selinux"""
    # This function is only for debugging and is not enabled by default
    # in rapidnode. Use at your own risk.
    username, password = get_credentials_children()
    command = "setenforce 0"
    cmd_debug(command)
    print(colored("Disabling selinux on child...\n", 'blue', attrs=['bold']))
    remote_cmd(child, username, password, command)


def parent_get_org_environments(capsule_id):
    """Get environments"""
    data = []
    environments = []
    username, password = get_credentials_parent()
    adminpassword = CONFIG['credentials']['adminpassword']
    command = ("hammer --username admin --password {0} --output csv "
               "capsule content available-lifecycle-environments "
               "--id {1}").format(adminpassword, capsule_id)
    cmd_debug(command)
    # TODO: Using old method for now, should clean it up,
    # and/but this function is an outlier in how the output
    # is interpreted.
    for results in paramiko_exec_command(PARENT, username, password, command):
        data.append(results)
    # Basically screen-scraping. What a hassle! is there a better way?
    environments = data[0].split("\n")
    environments.pop()
    environments.pop(0)
    return environments


def parent_get_capsules():
    """Ask the parent satellite for a list of all its capsules.

    :returns: A list of strings, where each string contains ``'id,name,url'``.
        For example: ``['1,example.com,https://example.com:9090']``.
    :rtype: str

    """
    username, password = get_credentials_parent()
    command = (
        'hammer --username admin --password {0} --output csv capsule list'
        .format(CONFIG['credentials']['adminpassword'])
    )
    cmd_debug(command)
    # The unit tests have examples of what paramiko_exec_command returns.
    return paramiko_exec_command(
        CONFIG['servers']['parent'],
        username,
        password,
        command
    )[0].decode(getdefaultlocale()[1]).split('\n')[1:-1]


def populate_capsules(parent):
    # This should be fixed.
    # (too-many-local-variables) pylint:disable=R0914
    """ Populates the capsules
    For now this needs to be run after ALL capsules have been created. This is
    because all content pushes are currently done via capsule id. It is very
    difficult to associate a capsule id with the capsule name we have provided
    at the beginning and have it make sense visually.

    In Other words, we can only sync by 'id', not by the 'hostname' users
    provided in the config settings.

    Note: If there exists a way to simply perform all the 'capsule content'
    functions via capsule name vs id, this can be easily remedied later.
    """
    print(colored("Determining all capsules...\n", 'blue', attrs=['bold']))
    capsules = parent_get_capsules()
    capsule_id = capsule_name = ""
    username, password = get_credentials_parent()
    adminpassword = CONFIG['credentials']['adminpassword']
    print(colored("Populating child capsule with environments...", 'blue',
                  attrs=['bold']))
    for cap in capsules:
        capsule_id, capsule_name = cap.split(",")[:2]
        # Don't try to do anything to default capsule
        if capsule_id != "1":
            print(colored("Populating capsule:", 'white',
                          attrs=['bold', 'underline']))
            print(colored(capsule_name, 'cyan', attrs=['bold']))
            print(colored("Determining applicable environments for capsule.\n",
                          'blue', attrs=['bold']))
            environments = parent_get_org_environments(capsule_id)
            for env in environments:
                env_id, env_name, env_org = env.split(",")
                print(colored('[' + env_org + '/' + env_name + ']', 'cyan'))
                command = ("hammer --username admin --password {0} "
                           "capsule content add-lifecycle-environment "
                           "--environment-id  {1} "
                           "--id {2}").format(adminpassword, env_id,
                                              capsule_id)
                cmd_debug(command)
                # It is okay to keep going on a non-zero here, because
                # re-running this script will trigger validation errors
                # on capsules where environments already exist, but these
                # errors have no ill effect - the pre-existing environments
                # will not be overwritten or otherwise modified.
                remote_cmd(
                    parent, username, password, command, halt_on_fail=False
                )
            # Using async below detaches us sooner and allows kickoff of
            # another capsule. But obviously we lose traceability from the
            # script side of things. I think it's ok, since we can always tail
            # log files on capsules.
            sync_command = ("hammer --username admin --password {0} "
                            "capsule content synchronize --async "
                            "--id {1}").format(adminpassword, capsule_id)
            print(colored(
                "Synchronizing capsule content...", 'blue', attrs=['bold']
            ))
            cmd_debug(sync_command)
            remote_cmd(
                parent, username, password, sync_command, halt_on_fail=False
            )


if __name__ == '__main__':
    main()
