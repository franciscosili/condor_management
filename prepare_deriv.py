#!/usr/bin/env python3
import argparse
import os
from lib.condor_base import condor_manager

# ==================================================================================================`
def mkdirp(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path
# ==================================================================================================`



parser = argparse.ArgumentParser()
parser.add_argument('--flavour' , type=str, help='job flavours / durations')
parser.add_argument('--cpus'    , type=int, help='number of cpus')
parser.add_argument('--ram'     , type=int, help='amount of ram')
parser.add_argument('--cmd'     , type=str, help='Command to execute')
parser.add_argument('--path_eos', type=str, help='Name of file that contains a path to where to cd at the moment of running condor')


parser.add_argument('--include_dirs'      , nargs='+', type=str, help='dirs to include when copying to condor. They are inside the path created by the versions')
parser.add_argument('--logs_dir'          , type=str, help='Dir to put submits and logs and outputs. They are inside the path created by the versions')
parser.add_argument('--use_dag'           , action='store_true', help='Use dags or standalone condor submits')


# parsing options for background tests
parser.add_argument('--nevents'         , type=int  , help='Number of events to generate')
parser.add_argument('--dsidrange'       , nargs='*', type=int, help='First and last DSID to run on.')

parser.add_argument('--cversion'          , type=str, help='calculation versions')
parser.add_argument('--tag'               , type=str, help='tag to add to the condor_submit filename and .sh file')

args = parser.parse_args()



#===================================================================================================
# FLAGS AND CONSTANTS, SETTING UP THE TOOL
#===================================================================================================
# from the 'output' path, then these folders come. Inside these folders there will be the JOs, gen and deriv
# directories
versions_path_results = mkdirp(f'results_v{args.cversion}')

if len(args.dsidrange) == 1:
    args.dsidrange.append(args.dsidrange[0]+1)




condor_mg = condor_manager(args.tag,
                            args.flavour,
                            args.cmd,
                            args.cpus,
                            args.ram,
                            args.logs_dir,
                            args.path_eos,
                            'output',
                            versions_path_results,
                            args.use_dag
                            )
#===================================================================================================
#===================================================================================================

print(args.dsidrange)

for this_dsid in range(*args.dsidrange):
    print(this_dsid)
    #===============================================================================================
    # PATHS AND OUTPUTS
    #===============================================================================================
    condor_mg.add_include_dirs([f'gen/{this_dsid}', ])
    condor_mg.exclude_dirs(['output', '.git', 'photonjetsignal/gen'])
    #===============================================================================================
    #===============================================================================================


    #===============================================================================================
    # RUN CREATION OF SCRIPTS
    #===============================================================================================
    # set of previous commands that need to be executed before running the python command


    # for each region we are going to create a directory, and then combine the ranges and dofs
    extra_path   = this_dsid
    extra_tag    = f'dsid{this_dsid}__evts{int(args.nevents/1000)}k'
    options_cmd  = f'--dsid {this_dsid} --nevents {args.nevents}'
    previous_cmd = 'check_command_success cd photonjetsignal\n'

    
    condor_mg.create_scripts(extra_path=extra_path,
                            extra_tag=extra_tag,
                            extra_cmds=f'{options_cmd} --cversion {args.cversion}',
                            previous_sh_cmds=previous_cmd,
                            setup_flags=' -d')
        
    if args.use_dag:
        condor_mg.save_dag()
    #===============================================================================================
    #===============================================================================================


