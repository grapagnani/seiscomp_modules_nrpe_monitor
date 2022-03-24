#!/usr/bin/python3

# Import

from lxml import etree
import re
import os
from datetime import datetime


# Configuration

global SCSOHLOG_XMLFILE
global STATE_RECORD_FILE
global MODULE_RESPONSE_FILE

SCSOHLOG_XMLFILE = "/home/seismo/.seiscomp/log/server.xml"
STATE_RECORD_FILE = "/dev/shm/seiscomp_modules_nrpe_monitor-staterecord.txt"
MODULE_RESPONSE_FILE = "/dev/shm/seiscomp_modules_nrpe_monitor-responsetime.txt"


# Class definition

class MonitoredService:
    def __init__(self, name, prog, xmlfile):
        self.name = name

        if re.search("[A-Z0-9]{8,}", name) or name == "MASTER":
            self.module_name = prog
        else:
            self.module_name = name

        if self.name == "MASTER":
            #self.watched_param = {'name':'objectcount', 'type':'int'}
            self.watched_param = {'name':'dbadds', 'type':'float'}
        else:
            self.watched_param = {'name':"sentmessages", 'type':"int"}

        self.param_value = -1
        self.param_updatetime = datetime.fromtimestamp(0)

        self.param_oldvalue = -1
        self.param_oldupdatetime = datetime.fromtimestamp(0)

        tree = etree.parse(xmlfile)
        for test in tree.xpath("/server/service[@name='%s']/test" % self.name):

            if test.get('name') == self.watched_param['name']:
                if self.watched_param['type'] == 'float':
                    self.param_value = float(test.get("value"))
                else:
                    self.param_value = int(test.get("value"))
                self.param_updatetime = get_timestamp(test.get("updateTime"))
                break

    def __repr__(self):
        if watched_param['type'] == 'float':
            msg = "module_name=%s, watched_param=%s, value=%f,"
            msg += "  updatetime%s, oldvalue=%f, oldupdatetime=%s"
        else:
            msg = "module_name=%s, watched_param=%s, value=%d,"
            msg += "  updatetime%s, oldvalue=%d, oldupdatetime=%s"

        return(msg
            % (self.module_name, self.watched_param['name'],
            self.param_value, self.param_updatetime,
            self.param_oldvalue, self.param_oldupdatetime))

    def staterecordline(self):
        line = "%s," % self.module_name

        if self.watched_param['type'] == 'float':
            msg = "%f,%d"
        else:
            msg = "%d,%d"

        if self.param_value == self.param_oldvalue:
            line += msg % \
                (self.param_oldvalue, int(self.param_oldupdatetime.timestamp()))

        else:
            line += msg % \
                (self.param_value, int(self.param_updatetime.timestamp()))

        return(line)

    def responsetime(self):
        if self.param_value != self.param_oldvalue:
            updatetime = self.param_updatetime
        else:
            updatetime = self.param_oldupdatetime

        responsetime = int(datetime.now().timestamp() - updatetime.timestamp())

        return(responsetime)

    def set_param_oldvalue(self, value):
        if self.watched_param['type'] == 'float':
            self.param_oldvalue = float(value)
        else:
            self.param_oldvalue = int(value)

    def set_param_oldupdatetime(self, value):
        self.param_oldupdatetime = datetime.fromtimestamp(int(value))

# Function definition

def get_timestamp(ts):
    timestamp = ts.replace('-', ':').replace('T', ':').replace('.', ':')
    timestamp = timestamp.split(':')[0:-1]
    timestamp = datetime(*(int(val) for val in timestamp))
    return(timestamp)

def get_previous_state_information(services, state_record_file):
    if os.path.isfile(state_record_file):
        with open(state_record_file) as fd:
            for line in fd:

                data = line.split(',')

                for svc in services:
                    if svc.module_name == data[0]:
                        svc.set_param_oldvalue(data[1])
                        svc.set_param_oldupdatetime(data[2])
                        break

def record_state_information(services, state_record_file):
    if os.path.isfile(state_record_file):
        os.remove(state_record_file)

    with open(state_record_file, 'w') as fd:
        for svc in services:
            fd.write("%s\n" % svc.staterecordline())

def record_modules_responsetime(services, module_response_file):
    if os.path.isfile(module_response_file):
        os.remove(module_response_file)

    with open(module_response_file, 'w') as fd:

        fd.write("lastupdate:%d\n" % int(datetime.now().timestamp()))

        for svc in services:
            fd.write("%s,%d\n" % (svc.module_name, svc.responsetime()))

def main():
    tree = etree.parse(SCSOHLOG_XMLFILE )

    services = []

    # get the information from scsohlog XML file
    for svc in tree.xpath("/server/service"):

        s = MonitoredService(
            svc.get("name"),
            svc.get("prog"),
            SCSOHLOG_XMLFILE
            )

        services.append(s)

    # get previous state information from the record file
    get_previous_state_information(services, STATE_RECORD_FILE)

    # write file used to record state of watched parameters
    record_state_information(services, STATE_RECORD_FILE)

    # write file with response time of each module
    record_modules_responsetime(services, MODULE_RESPONSE_FILE)

main()
