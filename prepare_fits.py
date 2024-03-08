import argparse, os, sys
from itertools import product

from condor_base import condor_manager

from lib.pathutils            import pathhelper_eos, pathhelper, pathhelper_condor_subs, condor_submit_path, common_path
from lib                      import parserutils
from lib                      import signalgrid
from lib.utils.boolean_parser import booleanArgument_defTrue

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
parser.add_argument('--flavour' , type=str, help='job flavours / durations')
parser.add_argument('--cpus'    , type=int, help='number of cpus')
parser.add_argument('--ram'     , type=int, help='amount of ram')
parser.add_argument('--cmd'     , type=str, help='Command to execute')
parser.add_argument('--notify'  , **booleanArgument_defTrue, help='Activate the notification via set-up in the condor submit files')


parserutils.samples_info_parser(parser)
parser.add_argument('--path'    , type=str, help='path for histograms')
parser.add_argument('--hversion', type=str, help='histograms versions')


parser.add_argument('--include_dirs', nargs='+', type=str, help='dirs to include when copying to condor. They are inside the path created by the versions in the output')
parser.add_argument('--logs_dir'    , type=str, help='Dir to put submits and logs and outputs. They are inside the path created by the versions')
parser.add_argument('--use_dag'     , action='store_true', help='Use dags or standalone condor submits')


# parsing options for background tests
parser.add_argument('--regions'         , nargs='*', type=str, help='Analysis regions. Optional')
parser.add_argument('--func_models'     , nargs='*', type=str, help='Functions. Optional')
parser.add_argument('--ranges'          , nargs='*', default=[], type=int, action='append', help='Fit ranges')

# signal parameters
parserutils.signal_params_parser(parser)


parser.add_argument('--tag'       , type=str, help='tag to add to the condor_submit filename and .sh file')

args = parser.parse_args()



# ==================================================================================================
# FLAGS AND CONSTANTS, SETTING UP THE TOOL
# ==================================================================================================`
# versions flags to pass to scripts
versions_flags       = f'--stype {args.stype} --sversion {args.sversion} -c {args.cversion} -H {args.hversion}'

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
    'local':  pathhelper.original_path.replace(common_path, '')[:-1],
    'remote': pathhelper_eos.original_path.replace(common_path, '')[:-1]
}
print(f'Output results will be written to:')
print(f'  - Local  eos: {path_results["local"]}')
print(f'  - Remote eos: {path_results["remote"]}')


# paths in eos local
pathhelper            .add_to_general_path(f'{args.path}/histograms_v{args.hversion}')
# paths in eos remote
pathhelper_eos        .add_to_general_path(f'{args.path}/histograms_v{args.hversion}')
# paths in afs for submits
pathhelper_condor_subs.add_to_general_path(f'{args.path}/histograms_v{args.hversion}')

pathhelper            .set_params({'stype': args.stype, 'sversion': args.sversion, 'cversion': args.cversion})
pathhelper_eos        .set_params({'stype': args.stype, 'sversion': args.sversion, 'cversion': args.cversion})
pathhelper_condor_subs.set_params({'stype': args.stype, 'sversion': args.sversion, 'cversion': args.cversion})

general_path_local            = pathhelper.get_path()
general_path_remote           = pathhelper_eos.get_path()
general_path_condor_submits   = pathhelper_condor_subs.get_path()


general_path_in_condor_output = f'{common_path}/{args.path}/histograms_v{args.hversion}'
general_path_in_condor_output = general_path_in_condor_output.format(**{'stype': args.stype,
                                                                        'sversion': args.sversion,
                                                                        'cversion': args.cversion}
                                                                    )





condor_mg = condor_manager(args.tag,
                           args.flavour,
                           args.cmd,
                           path_submits_logs     = pathhelper_condor_subs.get_path(args.logs_dir),
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
        (f'{general_path_local}/hists', f'')
    ],
    'exclude': [
        '.git',
        'run',
        'doc'
    ]
}
condor_mg.add_include_exclude_dirs(include_exclude_dict)



is_siginjtest = False
is_sstest     = False
if '--siginj' in args.cmd:
    is_siginjtest = True
elif '--sstest' in args.cmd:
    is_sstest = True


# ==================================================================================================`
# ==================================================================================================`

# ==================================================================================================
# RUN CREATION OF SCRIPTS
# ==================================================================================================
njobs = 0

for this_reg, this_range, this_func, this_model in product(args.regions, args.ranges, args.func_models, args.models):
    # for each region we are going to create a directory, and then combine the ranges and dofs
    this_range_str = f'range_{this_range[0]}-{this_range[1]}'

    extra_path     = f'{this_reg}/{this_range_str}__model_{this_func}'

    

    options_cmd    = f'--ranges {this_range[0]} {this_range[1]} --func_model {this_func} --regions {this_reg} --models {this_model}'


    fixed_parameters, is_qstar, is_gaus = signalgrid.get_fixed_parameters_list(this_model, args.f_vals,
                                                                               args.widths, args.ndims,
                                                                               args.quarks)

    for this_first_fixed_param, this_second_fixed_param in product(*fixed_parameters):
        # ------------------------------------------ GETTING PARAMETERS
        these_params, m_vals, fixed_params_str = \
                signalgrid.get_fixed_parameters_strings_mass_list(this_first_fixed_param,
                                                                  this_second_fixed_param,
                                                                  args.m_vals if not is_gaus else args.means,
                                                                  this_model,
                                                                  is_siginjtest)

        (this_quark, this_fval, this_width, this_ndim) = these_params

        if is_qstar:
            fixed_param_flag = f'--quarks {this_quark} --f_vals {this_fval}'
        elif is_gaus:
            fixed_param_flag = f'--widths {this_width}'
        else:
            fixed_param_flag = f'--ndims {this_ndim}'
        # ------------------------------------------------------------------------------------


        for this_mass in m_vals:
            
            if is_gaus:
                this_cmd_opt = f'{options_cmd} {fixed_param_flag} --means {this_mass}'
            else:
                this_cmd_opt = f'{options_cmd} {fixed_param_flag} --m_vals {this_mass}'


            extra_tag    = f'{this_reg}__{this_range_str}__{this_func}__{fixed_params_str}__m{this_mass}'

            condor_mg.create_scripts(extra_path       = extra_path,
                                     extra_tag        = extra_tag,
                                     extra_cmds       = f'{versions_flags} {this_cmd_opt}',
                                     previous_sh_cmds = 'tree .',
                                     setup_flags      = ' --default',
                                     reset_files      = False)

            njobs += 1

condor_mg.save_dag()
# ==================================================================================================`
# ==================================================================================================`

print('\n\n' + '='*100)
print(f'Total number of jobs = {njobs}')
print('='*100)