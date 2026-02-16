import argparse, os, sys
from itertools import product

from lib.condor.condor_base import condor_manager

#===================================================================================================
def mkdirp(path):
    if not os.path.exists(path): os.makedirs(path)
    return
#===================================================================================================



jobflavours = [
    'espresso',     # 20 minutes
    'microcentury', # 1 hour
    'longlunch',    # 2 hours
    'workday',      # 8 hours
    'tomorrow',     # 1 day
    'testmatch',    # 3 days
    'nextweek',     # 1 week
]


parser = argparse.ArgumentParser()
parser.add_argument('--flavour' , type=str, choices=jobflavours, help='job flavours / durations')
parser.add_argument('--cpus'    , type=int, help='number of cpus')
parser.add_argument('--ram'     , type=int, help='amount of ram')
parser.add_argument('--cmd'     , type=str, help='Command to execute')
parser.add_argument('--notify'  , action='store_true', help='Activate the notification via set-up in the condor submit files')

parser.add_argument('-o', "--output_path"    , type=str,
                    default='/eos/home-f/fsili/code/local/EGamma/PhotonID/FudgeFactorTool/output',
                    help="Ouput folder")
parser.add_argument('-e', "--output_path_eos", type=str,
                    default='/eos/home-f/fsili/Data/EGamma/PhotonID/outputs/FudgeFactorTool/partial_outputs',
                    help="Ouput folder for skim outputs")

parser.add_argument('-c', '--cversion', help='Version of calculation/results.')

parser.add_argument('--logs_dir', type=str, help='Dir to put submits and logs and outputs. They are inside the path created by the versions')
parser.add_argument('--use_dag' , action='store_true', help='Use dags or standalone condor submits')

# parsing options for samples
parser.add_argument('--samples', nargs='*', type=str, help='Which samples to use.')

parser.add_argument('--tag', type=str, help='tag to add to the condor_submit filename and .sh file')

args = parser.parse_args()

common_path            = f'results/results_v{args.cversion}'
condor_submit_path     = 'run/submits_condor/' + common_path



path             = f'{args.output_path}/{common_path}'
path_eos         = f'{args.output_path_eos}/{common_path}'
path_condor_subs = f'./{condor_submit_path}'



# ==================================================================================================
# FLAGS AND CONSTANTS, SETTING UP THE TOOL
# ==================================================================================================`
# versions flags to pass to scripts
versions_flags = f'-c {args.cversion}'
output_flags   = f'--output_path {args.output_path} --output_path_eos {args.output_path_eos}'

# In the case of the photonjet analysis, the condor submits will be done from within the repository, as it's already located in condor
"""
The submit files and logs will be saved in the path given by 'condor_path'
The outputs will be saved in the local computer at condor, and then transferred to EOS again.
There are two cases respecting the EOS outputs:
   - those which will be saved in the synced directory
   - those which are saved in directories which are not synced.
"""

# output paths in eos
path_results = {
    'local':  args.output_path,
    'remote': args.output_path_eos
}

print(f'Output results will be written to:')
print(f'  - Local  eos: {path_results["local"]}')
print(f'  - Remote eos: {path_results["remote"]}')


# paths in eos local
mkdirp(path            )
mkdirp(path_eos        )
mkdirp(path_condor_subs)


general_path_in_condor_output = common_path


condor_mg = condor_manager(args.tag,
                           args.flavour,
                           args.cmd,
                           path_submits_logs     = path_condor_subs.get_path(args.logs_dir),
                           path_results          = path_results,
                           path_output_in_condor = general_path_in_condor_output,
                           cpus                  = args.cpus,
                           ram                   = args.ram,
                           use_dag               = args.use_dag,
                           in_afs                = True,
                           notify                = args.notify,
                           )


include_exclude_dict = {
    'include': [
        # in case of having a tuple, first is the input path, second is the path in condor
        # the files will be copied to
        (f'{args.output_path}/ffs/comb/', f'')
    ],
    'exclude': [
        '.git',
        'run',
    ]
}
condor_mg.add_include_exclude_dirs(include_exclude_dict)


# ==================================================================================================`
# ==================================================================================================`

# ==================================================================================================
# RUN CREATION OF SCRIPTS
# ==================================================================================================
njobs = 0

for this_sample in args.samples:
    
    extra_path     = this_sample

    options_cmd    = f'{output_flags} --samples {this_sample}'

    condor_mg.create_scripts(extra_path       = extra_path,
                             extra_tag        = this_sample,
                             extra_cmds       = f'{versions_flags} {options_cmd}',
                             previous_sh_cmds = 'tree .',
                             reset_files      = False)
    njobs += 1

condor_mg.save_dag()
# ==================================================================================================`
# ==================================================================================================`

print('\n\n' + '='*100)
print(f'Total number of jobs = {njobs}')
print('='*100)