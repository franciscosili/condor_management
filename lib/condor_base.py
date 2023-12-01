from datetime import datetime
from .utils    import mkdirp, prepare_input_files, jobflavours, replace_in_string
import os, sys

# ==================================================================================================`
class condor_manager:
    # ==============================================================================================
    def __init__(self,
                 tag                  : str,
                 flavour              : str,
                 cpus                 : int,
                 ram                  : int,
                 logs_dirname         : str,
                 path_eos_file        : str,
                 path_results         : str,
                 general_path_results : str,
                 use_dag              : bool = True):
        
        if flavour not in jobflavours:
            print(f'Error: wrong job flavour entered. Options: {jobflavours}')
            sys.exit(1)


        self.tag         = tag
        self.flavour     = flavour
        self.cpus        = cpus
        self.ram         = ram
        self.now         = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.current_tag = f'{self.tag}__{self.now}'

        self.use_dag     = use_dag
        self.dag_addon   = 'dags' if self.use_dag else 'standalone'
        

        with open(path_eos_file, 'r') as f:
            self.path_eos = f.readline().strip('\n')

        self.project_name = path_eos_file.rsplit('/')[-1]


        # this path is given by versions generaly. This will be inside the general path in eios
        # this is the relative path from where this file is, to the location of the output logs and erorrs
        # files from condor
        self.general_path_results = general_path_results
        
        
        # where to store results in eos
        self.results_path         = f'{path_results}/{general_path_results}'
        
        
        # where logs will be saved. It can then contain multiple subdirectories
        self.condor_output_path = mkdirp(f'{general_path_results}/{logs_dirname}/{self.dag_addon}/{self.current_tag}')


        # setup executable and condor submit filenames and paths
        self.executable_filename    = f'job_condor__{self.current_tag}'
        self.condor_submit_filename = f'condor_submit__{self.current_tag}'

        if self.use_dag:
            self.dag_filename  = f'dag__{self.current_tag}.dag'
            self.dagfile       = f'{self.condor_output_path}/{self.dag_filename}'
        else:
            # name of executables and submits files
            self.executable_filename    = f'{self.executable_filename}.sh'
            self.condor_submit_filename = f'{self.condor_submit_filename}.sub'

            self.executable    = f'{self.condor_output_path}/{self.executable_filename}'
            self.condor_submit = f'{self.condor_output_path}/{self.condor_submit_filename}'



        self.dagfile_content = ''

        current_file_dir = os.path.dirname(__file__)
        with open(f'{current_file_dir}/templates/job_condor_TEMPLATE.sh', 'r') as inf:
            self.content_sh = inf.read()
        with open(f'{current_file_dir}/templates/condor_submit_TEMPLATE.sub', 'r') as inf:
            self.content_sub = inf.read()

        return
    # ==============================================================================================
    
    # ==============================================================================================
    def add_include_dirs(self, include_dirs):

        self.include_dirs_list = []

        if include_dirs:
            for d in include_dirs:
                merged_path = os.path.join(self.path_eos, self.results_path, d)
                
                if os.path.exists(merged_path):
                    self.include_dirs_list.append(merged_path)
                    print(f'Adding {merged_path} to the list of included directories to copy to condor')
                else:
                    print(f'Tried to add the following path which does not exist {merged_path}')

        return self.include_dirs_list
    # ==============================================================================================
    
    # ==============================================================================================
    def exclude_dirs(self, excluded_dirs):
        self.excluded_dirs = excluded_dirs
        return
    # ==============================================================================================
    
    # ==============================================================================================
    def setup_copying(self):
        return prepare_input_files(self.path_eos, self.excluded_dirs, self.include_dirs_list)
    # ==============================================================================================
    
    # ==============================================================================================
    def add_subdir_in_logs(self, subdirname):
        return mkdirp(f'{self.condor_output_path}/{subdirname}')
    # ==============================================================================================
    
    # ==============================================================================================
    def create_scripts(self, extra_path='', extra_tag='', extra_cmds=''):


        submits_logs_dir = self.condor_output_path
        if extra_path:
            submits_logs_dir = self.add_subdir_in_logs(extra_path)
        

        executable_filename    = self.executable_filename
        condor_submit_filename = self.condor_submit_filename

        if extra_tag != '':
            executable_filename    += f'__{extra_tag}.sh'
            condor_submit_filename += f'__{extra_tag}.sub'
        else:
            executable_filename    += '.sh'
            condor_submit_filename += '.sub'
        
        executable    = f'{submits_logs_dir}/{executable_filename}'
        condor_submit = f'{submits_logs_dir}/{condor_submit_filename}'


        # path of the .sub from the .dag file
        rel_path_dag_submits = os.path.relpath(submits_logs_dir, self.condor_output_path)


        cmd_copy, cmd_delete = self.setup_copying()


        # ------------------------------------------------------------------------------------------
        # SHELL FILE
        # ------------------------------------------------------------------------------------------
        shell_filename = f'{submits_logs_dir}/{executable_filename}'

        replace_in_string(self.content_sh, shell_filename, [
            ('CMD_COPY'   , cmd_copy),
            ('DELETEFILES', cmd_delete),
            ('CMD'        , f'{self.cmd} --cpus {self.cpus} --copy_out_files {self.path_eos} {extra_cmds}')
        ])
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------
        
        
        # ------------------------------------------------------------------------------------------
        # CONDOR SUBMIT FILE
        # ------------------------------------------------------------------------------------------
        sub_filename = f'{submits_logs_dir}/{condor_submit_filename}'

        replace_in_string(self.content_sub, sub_filename, [
            ('EXECUTABLE'  , executable_filename),
            ('OUTPATH'     , ''),
            ('CPUS'        , self.cpus),
            ('RAM'         , self.ram),
            ('FLAVOUR'     , self.flavour),
        ])
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------
        
        
        # ------------------------------------------------------------------------------------------
        # DAG FILE
        # ------------------------------------------------------------------------------------------
        self.dag_file_contents += f'JOB {extra_tag if extra_tag else self.tag} {condor_submit_filename} DIR {rel_path_dag_submits}\n'
        # ------------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------------

        return
    # ==============================================================================================
    
    # ==============================================================================================
    def save_dag(self):
        with open(self.dagfile, 'w') as outdag:
            outdag.write(self.dag_file_contents)
        return
    # ==============================================================================================
# ==================================================================================================


