import argparse, os
from lib.condor_base import condor_manager
from itertools import product

jobflavours = [
    'espresso',     # 20 minutes
    'microcentury', # 1 hour
    'longlunch',    # 2 hours
    'workday',      # 8 hours
    'tomorrow',     # 1 day
    'testmatch',    # 3 days
    'nextweek',     # 1 week
]

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

parser.add_argument('--sversion', type=str, help='samples versions')
parser.add_argument('--cversion', type=str, help='calculation versions')
parser.add_argument('--hpath'   , type=str, help='path for histograms')
parser.add_argument('--histograms_version', type=str, help='histograms versions')
parser.add_argument('--include_dirs'      , nargs='+', type=str, help='dirs to include when copying to condor. They are inside the path created by the versions')
parser.add_argument('--logs_dir'          , type=str, help='Dir to put submits and logs and outputs. They are inside the path created by the versions')
parser.add_argument('--use_dag'           , action='store_true', help='Use dags or standalone condor submits')


# parsing options for background tests
parser.add_argument('--regions'    , nargs='*', type=str, help='Analysis regions. Optional')
parser.add_argument('--func_models', nargs='*', type=str, help='Functions. Optional')
parser.add_argument('--ranges'     , nargs='*', default=[], type=int, action='append', help='Fit ranges')


parser.add_argument('--tag'       , type=str, help='tag to add to the condor_submit filename and .sh file')

args = parser.parse_args()



# ==================================================================================================
# FLAGS AND CONSTANTS, SETTING UP THE TOOL
# ==================================================================================================`
# versions flags to pass to scripts
versions_flags       = f'-v {args.sversion} -c {args.cversion} -H {args.histograms_version}'
general_path_results = mkdirp(f'samples__v{args.sversion}/results_v{args.cversion}/{args.hpath}/histograms_v{args.histograms_version}')


condor_mg = condor_manager(args.tag,
                           args.flavour,
                           args.cpus,
                           args.ram,
                           args.logs_dir,
                           args.path_eos,
                           'run/results',
                           general_path_results,
                           args.use_dag
                           )
# ==================================================================================================`
# ==================================================================================================`

# ==================================================================================================
# PATHS AND OUTPUTS
# ==================================================================================================
condor_mg.add_include_dirs(args.include_dirs)
condor_mg.exclude_dirs(['run', '.git'])
# ==================================================================================================`
# ==================================================================================================`


# ==================================================================================================
# RUN CREATION OF SCRIPTS
# ==================================================================================================
for this_reg, this_range, this_func in product(args.regions, args.ranges, args.func_models):
    # for each region we are going to create a directory, and then combine the ranges and dofs
    this_range_str = f'range_{this_range[0]}-{this_range[1]}'

    extra_path     = f'{this_reg}/{this_range_str}__model_{this_func}'

    extra_tag      = f'{this_reg}__{this_range_str}__{this_func}'

    options_cmd    = f'--ranges {this_range[0]} {this_range[1]} --func_model {this_func} --regions {this_reg}'

    condor_mg.create_scripts(extra_path=extra_path,
                             extra_tag=extra_tag,
                             extra_cmds=f'{versions_flags} {options_cmd}')
    
condor_mg.save_dag()
# ==================================================================================================`
# ==================================================================================================`


