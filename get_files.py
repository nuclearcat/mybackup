#!/usr/bin/env python3
'''
Collectd backup info, from Linux, Cisco, Mikrotik, Juniper to files
'''

import os
import sys
import yaml
import paramiko
import scp
import argparse

config = {}

'''
yaml config for this program:
---
datadir: ./data
hosts:
    - name: pppoe9
        type: gos
        host: 10.0.252.9
        username: root
        key: .ssh_id_ecdsa
        backup:
            - /mnt/flash/secure2/config.tgz

    - name: junipercore
        type: junos
        host: 10.0.252.1
        username: admin
        key: .ssh_id_ecdsa

'''

def get_file(host, key, user, filepath):
    # use paramiko scp
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, key_filename=key)
    scpclient = scp.SCPClient(ssh.get_transport())
    dst_filename = host+'_'+filepath.replace('/', '_')
    scpclient.get(filepath, config['datadir']+'/'+dst_filename)
    scpclient.close()
    ssh.close()


def iterate_items(host):
    for item in host['backup']:
        print("Backing up", item)
        # if not ends with / then its file
        if not item.endswith('/'):
            get_file(host['host'], host['key'], host['username'], item)



def load_config(configname):
    global config
    with open(configname) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    # verify datadir and if not exist create it
    if not os.path.isdir(config['datadir']):
        print("Data directory", config['datadir'], "does not exist, creating it")
        # recursively create directory
        os.makedirs(config['datadir'])

def backup_gos(name):
    global config
    for host in config['hosts']:
        if host['name'] == name:
            print("Backing up", host['name'], "type", host['type'])
            # iterate over backup items
            iterate_items(host)


def install_systemd():
    # check for root privileges
    if os.geteuid() != 0:
        print("This program must be run as root")
        sys.exit(1)
    # install itself to /usr/local/bin
    os.system("cp get_files.py /usr/local/bin/get_files.py")
    # create systemd timer
    with open('get_files.timer', 'w') as f:
        f.write('''[Unit]
Description=Get backup files timer

[Timer]
Unit=get_files.service
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
''')
    # create systemd service
    with open('get_files.service', 'w') as f:
        f.write('''[Unit]
Description=Get backup files service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/get_files.py --config /etc/backup.yaml

[Install]
WantedBy=multi-user.target
''')
    # copy systemd files to /etc/systemd/system
    os.system("cp get_files.timer /etc/systemd/system/get_files.timer")
    os.system("cp get_files.service /etc/systemd/system/get_files.service")
    # enable systemd timer
    os.system("systemctl enable get_files.timer")
    # start systemd timer
    os.system("systemctl start get_files.timer")


def main():
    argparser = argparse.ArgumentParser(description='Collectd backup info, from Linux, Cisco, Mikrotik, Juniper to files')
    argparser.add_argument('--config', help='Config file name', default='config.yaml')
    # genkey (generate ecdsa-sha2-nistp256 key)
    argparser.add_argument('--genkey', help='Generate key file')
    # install systemd timer
    argparser.add_argument('--install', help='Install systemd timer', action='store_true')

    args = argparser.parse_args()

    if args.genkey:
        print(f"Generating key {args.genkey}")
        os.system(f"ssh-keygen -t ecdsa -b 256 -f {args.genkey}")
        sys.exit(0)
    
    if args.install:
        install_systemd()

    load_config(args.config)
    # validate if ssh keys exist
    for host in config['hosts']:
        if not os.path.isfile(host['key']):
            print("SSH key", host['key'], "does not exist, you can generate it with --genkey ", host['key'])
            sys.exit(1)
    # iterate over hosts
    for host in config['hosts']:
        if host['type'] == 'gos':
            backup_gos(host['name'])
        elif host['type'] == 'junos':
            print("Junos not implemented yet")
        else:
            print("Unknown host type", host['type'])


if __name__ == "__main__":
    main()