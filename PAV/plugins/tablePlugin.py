#!python

#  ###################################################################
#
#  Disclaimer and Notice of Copyright 
#  ==================================
#
#  Copyright (c) 2015, Los Alamos National Security, LLC
#  All rights reserved.
#
#  Copyright 2015. Los Alamos National Security, LLC. 
#  This software was produced under U.S. Government contract 
#  DE-AC52-06NA25396 for Los Alamos National Laboratory (LANL), 
#  which is operated by Los Alamos National Security, LLC for 
#  the U.S. Department of Energy. The U.S. Government has rights 
#  to use, reproduce, and distribute this software.  NEITHER 
#  THE GOVERNMENT NOR LOS ALAMOS NATIONAL SECURITY, LLC MAKES 
#  ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY 
#  FOR THE USE OF THIS SOFTWARE.  If software is modified to 
#  produce derivative works, such modified software should be 
#  clearly marked, so as not to confuse it with the version 
#  available from LANL.
#
#  Additionally, redistribution and use in source and binary 
#  forms, with or without modification, are permitted provided 
#  that the following conditions are met:
#  -  Redistributions of source code must retain the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer. 
#  -  Redistributions in binary form must reproduce the 
#     above copyright notice, this list of conditions 
#     and the following disclaimer in the documentation 
#     and/or other materials provided with the distribution. 
#  -  Neither the name of Los Alamos National Security, LLC, 
#     Los Alamos National Laboratory, LANL, the U.S. Government, 
#     nor the names of its contributors may be used to endorse 
#     or promote products derived from this software without 
#     specific prior written permission.
#   
#  THIS SOFTWARE IS PROVIDED BY LOS ALAMOS NATIONAL SECURITY, LLC 
#  AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
#  IN NO EVENT SHALL LOS ALAMOS NATIONAL SECURITY, LLC OR CONTRIBUTORS 
#  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, 
#  OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
#  OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
#  OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
#  OF SUCH DAMAGE.
#
#  ###################################################################


""" plugin that implements the table command
"""

import os
import re # pattern matching in file
import fnmatch # finding log files
import time # start timespan
import sys
from yapsy.IPlugin import IPlugin
from testConfig import YamlTestConfig
import subprocess
import logging
#from testEntry import TestEntry


class GetResults(IPlugin):
    """ This implements the plugin, or command, to get a summary of
        test results.
    """

    logger = logging.getLogger(__name__)

    def __init__(self):
        my_name = self.__class__.__name__
        self.logger.info('created instance of plugin: %s' % my_name)

    # Every plugin class MUST have a method by the name "add_parser_info"
    # and must return the name of the the sub-command

    def add_parser_info(self, subparser):
        parser_gr = subparser.add_parser("table", help = "show test results")

        parser_gr.add_argument('-t', nargs = 1, metavar = '<string>', help = "test name to match on")
        parser_gr.add_argument('-u', nargs = 1, metavar = '<segment_name>', help = "target segment to match on")

        parser_gr.add_argument('-s', nargs = 1, metavar = '<string>', 
                                help = "enqueue date/time minimum (yyyy-mm-ddThh:mm:ss), default 15 days ago")
        parser_gr.add_argument('-S', nargs = 1, metavar = '<string>',
                                help = "enqueue date/time maximum (yyyy-mm-ddThh:mm:ss), default is now")
        parser_gr.add_argument('-e', nargs = 1, metavar = '<string>', 
                                help = "end date/time minimum (yyyy-mm-ddThh:mm:ss), default is 15 days ago")
        parser_gr.add_argument('-E', nargs = 1, metavar = '<string>', 
                                help = "end date/time maximum (yyyy-mm-ddThh:mm:ss), default is now.")

        parser_gr.add_argument('-f', '--fail', help = "locate/show failed tests", action = "store_true")
        parser_gr.add_argument('-i', '--inc', help = "locate/show 'incomplete' tests", action = "store_true")
        parser_gr.add_argument('-p', '--pass', help = "locate/show passing tests", action = "store_true")
        parser_gr.add_argument('-F', '--exclude-fail', help = "exclude failed tests", action = "store_true")
        parser_gr.add_argument('-I', '--exclude-inc', help = "exclude 'incomplete' tests", action = "store_true")
        parser_gr.add_argument('-P', '--exclude-pass', help = "exclude passing tests", action = "store_true")

        parser_gr.add_argument('-v', '--verbose', help = "show work", action = "store_true")

        parser_gr.add_argument('-m', '--maxsize', nargs = 1, metavar = '<int>', help = 'maximum file size,'
                                             ' I wont open larger log files. Default = no limit')

        parser_gr.add_argument('-d', '--delimiter', nargs = 1, metavar = '<string>',
                                 help = 'column delimiter, default is space')

        parser_gr.add_argument('-ts', nargs = 1, metavar = '<file>',
                               help = 'test suite to acquire results path (root) from,'
                                    ' else I will look in the current directory')

        parser_gr.add_argument('-o', nargs = 1, metavar = '<string>',
                               help = "select new fields to display in the form 'f1 f2 f3'"
                                    "  possibilities are (f)ilename (r)esult (s)tart_time "
                                    "  (e)nd_time (n)ame n(o)des (c)ores or (d)FIELD"
                                    "  FIELD matches any line starting with <FIELD>"
                                    "  Default pattern is the environment variable PTH_TABLEFORMAT or 'n r s e'")

        parser_gr.set_defaults(sub_cmds = 'table')
        return 'table'

    # Every plug-in (command) MUST have a method by the name "cmd".
    # It will be what is called when that command is selected.
    def cmd(self, args):

        if args['verbose']:
            print "Command args -> %s" % args

        if args['delimiter']:
            delim=str(args['delimiter'][0])
            if args['verbose']:
                print 'delimiter is "' + delim + '"'
        else:
            delim=" "

        # NOTE if maxfilesize becomes 0 it will be logically equivalent to None
        # below and not checked.  So zero is equivalent to infinity here.
        if args['maxsize']:
            maxfilesize=int(args['maxsize'][0])
        else:
            # default to 100 mb
            maxfilesize=None

        # is test_suite specified?
        if args['ts']:
            dts = str(args['ts'][0])
            tc = YamlTestConfig(dts)
            tsc = tc.get_effective_config_file()
            if args['verbose']:
                print "effective test suite configuration:"
                print tsc
            res_loc_list = tc.get_result_locations()
        else:
            if args['verbose']:
                print "will look in the working directory ..."
            res_loc_list = [os.getcwd()]
        if args['verbose']:
            print res_loc_list

        # establish time window
        # we'll need this for start time constraints
        # getting time in epoch form so it's easy to subtract and compare
        now = time.mktime(time.localtime())
        mdytimeformat = "%m-%d-%YT%H:%M:%S"
        ymdtimeformat = "%Y-%m-%dT%H:%M:%S"
        # default is 15 days ago to now
        starttimeinterval = (time.localtime(now-1296000), time.localtime(now)) 
        endtimeinterval = (time.localtime(now-1296000), time.localtime(now)) 
        if args['s']:
             starttimeinterval = (time.strptime(args['s'][0], ymdtimeformat), starttimeinterval[1])
        if args['S']:
             starttimeinterval = (starttimeinterval[0], time.strptime(args['S'][0], ymdtimeformat))
        if args['e']:
             endtimeinterval = (time.strptime(args['e'][0], ymdtimeformat), endtimeinterval[1])
        if args['E']:
             endtimeinterval = (endtimeinterval[0], time.strptime(args['E'][0], ymdtimeformat))
        if args['verbose']:
            print "showing tests that start in the interval: " + str(starttimeinterval)
            print "showing tests that end in the interval: " + str(endtimeinterval)

        # output format
        if args['o']:
            outputform = args['o'][0].split()
        elif ( "PTH_TABLEFORMAT" in os.environ ):
            outputform = os.environ["PTH_TABLEFORMAT"].split()
            if args['verbose']:
                print "using PTH_TABLEFORMAT: " + os.environ["PTH_TABLEFORMAT"]
        else:
            outputform = ['n', 'r', 's', 'e']

        outputheader = []
        for field in outputform:
            if field == "f":
                outputheader.append( "filename" )
            if field == "r":
                outputheader.append( "result" )
            if field == "s":
                outputheader.append( "start-time" )
            if field == "e":
                outputheader.append( "end-time" )
            if field == "n":
                outputheader.append( "test-name" )
            if field == "o":
                outputheader.append( "#nodes" )
            if field == "c":
                outputheader.append( "#cores" )
            if field[0] == "d":
                outputheader.append( field[1:] )

        # get the results log files
        outputlist = []
        logfilecount = 0
        for results_dir in res_loc_list:
            if not os.path.isdir(results_dir):
                print "pav: error: looking in an invalid directory: "+ str(results_dir)
            else:
                for base, dirs, files in os.walk(results_dir):
                    for alogfile in fnmatch.filter(files, "*.log"):

                        logfilecount += 1

                        if args['verbose']:
                            print "considering log file: "+base+"/"+alogfile

                        # check file name match before opening the file
                        # NOTE, assuming that the file name will contain the test name
                        #       otherwise we need to parse test name out of contents
                        if args['t'] and not args['t'][0] in alogfile:
                            if args['verbose']:
                                print " doesnt match test name pattern"
                            continue

                        # enqueue time is in the directory path, don't need to open the file yet
                        starttime = re.search("[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+", base)
                        if starttime:
                            starttime = time.strptime(str(starttime.group(0)), ymdtimeformat)
                        # if we didnt get a start time, assume it is okay
                        if starttime and not ( starttime >= starttimeinterval[0] and starttime <= starttimeinterval[1] ):
                            if args['verbose']:
                                print " start outside allowed interval"
                            continue

                        # is file "too big"?
                        # better warn here anyway so we know when files are skipped
                        if ( maxfilesize and os.stat(base + "/" + alogfile).st_size > maxfilesize ):
                            if args['verbose']:
                                print " file size is greater than maximum allowed : " + \
                                    str(os.stat(base + "/" + alogfile).st_size) + " > " + str(maxfilesize)
                            continue

                        contents = open(base+"/"+alogfile, 'r').read()

                        # check pass/fail
                        failed = False
                        passed = False
                        state = "I"
                        if "<result> failed" in contents:
                            failed = True
                            state = "F"
                        elif "<result> passed" in contents:
                            passed = True
                            state = "P"
                        # get out if we weren't interested in that kind of result
                        if failed and ( args['pass'] or args['inc'] or args['exclude_fail'] ):
                            if args['verbose']:
                                print " doesn't match pass/fail conditions"
                            continue
                        if passed and ( args['fail'] or args['inc'] or args['exclude_pass'] ):
                            if args['verbose']:
                                print " doesn't match pass/fail conditions"
                            continue
                        if not passed and not failed and ( args['fail'] or args['pass'] or args['exclude_inc'] ):
                            if args['verbose']:
                                print " doesn't match pass/fail conditions"
                            continue

                        # we checked start time above
                        endtime = re.search("<end>.*", contents)
                        # endtime is either after "<end>" or after "remove WS:"
                        if endtime:
                            # convert it to epoch seconds
                            endtime = time.strptime(str(endtime.group(0).split()[1]), mdytimeformat)
                        else:
                            endtime = re.search("remove WS:.*\.([0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+)", contents)
                            if endtime:
                                endtime = time.strptime(str(endtime.group(1)), mdytimeformat)
                            
                        if endtime and not ( endtime >= endtimeinterval[0] and endtime <= endtimeinterval[1] ):
                            if args['verbose']:
                                print " end outside allowed interval"
                            continue

                        # need a specific target segment?
                        # in this case no segment doesnt match
                        segment = re.search("<target_seg> (.*)", contents)
                        if segment:
                            segment = str(segment.group(1))
                        if args["u"] and ( not segment or not args['u'][0] in segment ):
                            if args['verbose']:
                                print " target segment doesn't match " +args['u'][0] + "<>" +str(segment)
                            continue

                        # store the required fields for pretty printing later
                        output = []
                        for field in outputform:
                            if field == 'f':
                                output.append( base + "/" + alogfile )
                            if field == 'r':
                                output.append( state )
                            if field == 's':
                                if starttime:
                                    output.append(time.strftime(ymdtimeformat, starttime))
                                else:
                                    output.append("")
                            if field == 'e':
                                if endtime:
                                    output.append(time.strftime(ymdtimeformat, endtime))
                                else:
                                    output.append("")
                            if field == 'n':
                                # still assuming logfile name == test name
                                output.append( alogfile[:-4] )
                            if field == 'o':
                                numnodes = re.search("<nnodes> (.*)", contents)
                                if numnodes:
                                    output.append( str(numnodes.group(1)) )
                                else:
                                    output.append("")
                            if field == 'c':
                                npes = re.search("<npes> (.*)", contents)
                                if numnodes:
                                    output.append( str(npes.group(1)) )
                                else:
                                    output.append("")
                            if field[0] == 'd':
                                found = re.search("<"+field[1:]+"> (.*)", contents)
                                if found:
                                    output.append( found.group(1) )
                                else:
                                    output.append("")
                            
                        outputlist.append(output)

        # space buffered table
        # we could use a package to make this easier, but I dont want to add a dependency
        bufferlist = []
        for f in outputheader:
            bufferlist.append(len(f))
        for l in outputlist:
            for fn in range(len(l)):
                if len(l[fn]) > bufferlist[fn]:
                    bufferlist[fn] = len(l[fn]) 

        for fn in range(len(outputheader)):
            print outputheader[fn] + " "*(bufferlist[fn]-len(outputheader[fn])) + delim,
        print ""
        for l in outputlist:
            for fn in range(len(l)):
                print l[fn] + " "*(bufferlist[fn]-len(l[fn])) + delim,
            print ""

        print "\n" + str(len(outputlist)) + " results found out of " + str(logfilecount) + " .log files"


if __name__ == "__main__":
    print table.__doc__
