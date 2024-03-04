from datetime import datetime
from condor_utils    import mkdirp, get_paths_file, replace_in_string, prepare_include_copy_cmd, prepare_exclude_copy_cmd
import os, sys

from typing import Union, Dict, List

# ==================================================================================================`
class condor_manager:
    # ==============================================================================================
    def __init__(self,
                 tag                     : str,
                 flavour                 : str,
                 cmd                     : str,
                 path_submits_logs       : str,
                 path_results            : Dict[str, str],
                 path_output_in_condor   : int,
                 extra_path_submits_logs : str = None,
                 cpus                    : int = 2,
                 ram                     : int = 2,
                 use_dag                 : bool = True,
                 in_afs                  : bool = True,
                 notify                  : bool = True) -> None:
        """
        Class that automatically manages dags, submits, shell files and sets up everything to run with condor.

        Args:
            tag                   (str): extra tag to put to filenames and to the jobs
            flavour               (str): flavour of the condor job
            cmd                   (str): command to execute inside the .sh file that will be submitted
            path_submits_logs     (str): path to the submits and log files. It is only defined in afs
            path_results          (dict[str, str]): Dictionary with paths to the different outputs. It may have different
                                                    keys which define different places where to store outputs
            cpus                  (int): number of CPUs to use
            ram                   (int): amount of RAM needed
            use_dag               (bool, optional): Whether to use dags or simple condor submits. Defaults to True.
        """

        self.tag         = tag
        self.flavour     = flavour
        self.cmd         = cmd
        self.cpus        = cpus
        self.ram         = ram
        self.now         = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.current_tag = f'{self.tag}__{self.now}'

        self.use_dag     = use_dag
        self.dag_addon   = 'dags' if self.use_dag else 'standalone'
        
        self.in_afs      = in_afs
        self.notify      = notify

        # Paths to store the submits/shells/dag files
        self.path_submits_logs = path_submits_logs
        if extra_path_submits_logs is not None:
            self.path_submits_logs += f'/{extra_path_submits_logs}'
        self.path_submits_logs += f'/{self.dag_addon}/{self.current_tag}'
        mkdirp(self.path_submits_logs)


        # Paths to store all outputs
        self.path_results = path_results
        for v in self.path_results.values():
            mkdirp(v)
            


        # Output path for files inside condor
        self.output_in_condor_path = path_output_in_condor
        # mkdirp(self.output_in_condor_path)
        

        # setup executable and condor submit filenames and paths
        self.executable_filename    = f'job_condor__{self.current_tag}'
        self.condor_submit_filename = f'condor_submit__{self.current_tag}'

        if self.use_dag:
            self.dag_filename  = f'dag__{self.current_tag}.dag'
            self.dagfile       = f'{self.path_submits_logs}/{self.dag_filename}'
        
        else:
            # name of executables and submits files
            self.executable_filename    = f'{self.executable_filename}'
            self.condor_submit_filename = f'{self.condor_submit_filename}'

            self.executable    = f'{self.path_submits_logs}/{self.executable_filename}'
            self.condor_submit = f'{self.path_submits_logs}/{self.condor_submit_filename}'

        self.dagfile_content = ''

        with open(f'condor/templates/job_condor_TEMPLATE.sh', 'r') as inf:
            self.content_sh = inf.read()
        with open(f'condor/templates/condor_submit_TEMPLATE.sub', 'r') as inf:
            self.content_sub = inf.read()

        return
    # ==============================================================================================
    
    # ==============================================================================================
    def add_include_exclude_dirs(self, include_exclude_dirs_dict : List[str]) -> None:

        self.include_dirs_cmds = []

        for d in include_exclude_dirs_dict['include']:
            # We have a path with input, and output
            output_path = os.path.join(self.output_in_condor_path, d[1])

            self.include_dirs_cmds += prepare_include_copy_cmd(input_path  = d[0],
                                                                output_path = output_path)

        
        exclude_dirs_cmds, self.cmds_del = prepare_exclude_copy_cmd(os.getcwd(),
                                                                    include_exclude_dirs_dict)

        self.include_dirs_cmds += exclude_dirs_cmds
    # ==============================================================================================
    
    # ==============================================================================================
    def add_subdir_in_logs(self, subdirname : str) -> str:
        return mkdirp(f'{self.path_submits_logs}/{subdirname}')
    # ==============================================================================================
    
    # ==============================================================================================
    def create_scripts(self,
                       extra_path       : str  = '',
                       extra_tag        : str  = '',
                       extra_cmds       : str  = '',
                       previous_sh_cmds : str  = '',
                       setup_flags      : str  = '',
                       reset_files      : bool = True) -> None:

        submits_logs_dir = self.path_submits_logs
        
        if extra_path:
            # extra path to add to the logfiles
            submits_logs_dir = self.add_subdir_in_logs(extra_path)
        

        executable_filename    = self.executable_filename
        condor_submit_filename = self.condor_submit_filename

        if extra_tag != '':
            executable_filename    += f'__{extra_tag}.sh'
            condor_submit_filename += f'__{extra_tag}.sub'
        else:
            executable_filename    += '.sh'
            condor_submit_filename += '.sub'
        

        # path of the .sub from the .dag file
        rel_path_dag_submits = os.path.relpath(submits_logs_dir, self.path_submits_logs)


        cmd_copy = '\n'.join(self.include_dirs_cmds)
        cmd_del  = self.cmds_del

        setup_command = f'check_command_success source setup.sh'


        # modify actual command
        cmd = self.cmd
        if self.cpus:
            cmd += f' --cpus {self.cpus}'
        
        extra_cmds += f' --copy_out_files {self.path_results["local"]} --copy_out_files_remote {self.path_results["remote"]}'

        # ------------------------------------------------------------------------------------------
        # SHELL FILE
        # ------------------------------------------------------------------------------------------
        shell_filename = f'{submits_logs_dir}/{executable_filename}'

        replace_in_string(self.content_sh, shell_filename, [
            ('PREVIOUSCOMMANDS', previous_sh_cmds),
            ('SETUPCOMMAND'    , setup_command + setup_flags),
            ('COPYCOMMAND'     , cmd_copy),
            ('DELETEFILES'     , cmd_del),
            ('CMD'             , f'{cmd} {extra_cmds}')
        ])
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------
        
        
        # ------------------------------------------------------------------------------------------
        # CONDOR SUBMIT FILE
        # ------------------------------------------------------------------------------------------
        sub_filename = f'{submits_logs_dir}/{condor_submit_filename}'

        set_cpu = ''
        set_ram = ''
        if self.cpus is not None:
            set_cpu = f'request_cpus    =   {self.cpus}'
        if self.ram is not None:
            set_ram = f'request_memory    =   {self.ram}GB'

        replace_in_string(self.content_sub, sub_filename, [
            ('EXECUTABLE'  , executable_filename),
            ('OUTPATH'     , ''),
            ('CPUS'        , set_cpu),
            ('RAM'         , set_ram),
            ('FLAVOUR'     , self.flavour),
        ])
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------
        
        
        # ------------------------------------------------------------------------------------------
        # DAG FILE
        # ------------------------------------------------------------------------------------------
        self.dagfile_content += f'JOB {extra_tag if extra_tag else self.tag} {condor_submit_filename} DIR {rel_path_dag_submits}\n'
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------

        if reset_files:
            self.reset_files()
        return
    # ==============================================================================================
    
    # ==============================================================================================
    def reset_files(self) -> None:
        self.include_dirs_cmds.clear()
        return
    # ==============================================================================================
    
    # ==============================================================================================
    def save_dag(self) -> None:
        with open(self.dagfile, 'w') as outdag:
            outdag.write(self.dagfile_content)
        return
    # ==============================================================================================
# ==================================================================================================


