from datetime import datetime
from .utils    import mkdirp, prepare_input_files, jobflavours, replace_in_string
import os, sys

# ==================================================================================================`
class condor_manager:
    # ==============================================================================================
    def __init__(self,
                 tag                  : str,
                 flavour              : str,
                 cmd                  : str,
                 cpus                 : int,
                 ram                  : int,
                 logs_dirname         : str,
                 path_eos_file        : str,
                 path_results         : str,
                 versions_path_results : str,
                 use_dag              : bool = True):
        """
        The general case for paths will be given with this example
        /eos/home-f/fsili/code/local/Resonances/code/PJA/photonjetanalysis/run/results/samples__v29_0/results_v0/jfakes/jfakes_v1/2-template_fits

        path_eos_file: From this path, the name of the project will be guessed. It has several functions:
            - path where the final copy of results will be done.
            - path which will be used to know which files will be copied to condor
        versions_path_results: This is a continuation of versions making up the final version of the calculation.
            From the first output folder, these directories come, combining different versions of calculations,
            samples, etc. These are simply of the form:
                'samples_vX/results_vY/histograms_vZ'

        From the example,
        path_results = run/results
                
        Args:
            tag                   (str): extra tag to put to filenames and to the jobs
            flavour               (str): flavour of the condor job
            cmd                   (str): command to execute inside the .sh file that will be submitted
            cpus                  (int): number of CPUs to use
            ram                   (int): amount of RAM needed
            logs_dirname          (str): _description_
            path_eos_file         (str): path to .txt file containing a path to EOS where the original project is. 
            path_results          (str): Path between project name and where versions_path_results is
            versions_path_results (str): path indicating versions
            use_dag               (bool, optional): Whether to use dags or simple condor submits. Defaults to True.
        """

        self.tag         = tag
        self.flavour     = flavour
        self.cpus        = cpus
        self.ram         = ram
        self.cmd         = cmd
        self.now         = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.current_tag = f'{self.tag}__{self.now}'

        self.use_dag     = use_dag
        self.dag_addon   = 'dags' if self.use_dag else 'standalone'
        

        # self.path_eos, from the given example path, is
        #   /eos/home-f/fsili/code/local/Resonances/code/PJA/photonjetanalysis
        self.path_eos2 = ''
        with open(path_eos_file, 'r') as f:
            lines = f.readlines()
            self.path_eos = lines[0].strip('\n')
            if len(lines) > 1:
                if lines[1].strip('\n'):
                    self.path_eos2 = lines[1].strip('\n')

            

        # self.project_name is
        #   photonjetanalysis
        self.project_name = path_eos_file.rsplit('/')[-1]


        # this path is given by versions generaly. This will be inside the general path in eos, self.path_eos
        # self.versions_path_results is
        #   samples__v29_0/results_v0/jfakes/jfakes_v1
        self.versions_path_results = versions_path_results
        
        
        # where to store results in eos. From the project directory in eos, this path points directly to the outputs
        # self.results_path is
        #   run/results/samples__v29_0/results_v0/jfakes/jfakes_v1
        self.results_path         = f'{path_results}/{versions_path_results}'
        
        
        # where logs will be saved. It can then contain multiple subdirectories
        # self.condor_output_path is
        #   samples__v29_0/results_v0/jfakes/jfakes_v1/<logs_dirname>/...
        self.condor_output_path = mkdirp(f'{versions_path_results}/{logs_dirname}/{self.dag_addon}/{self.current_tag}')


        # setup executable and condor submit filenames and paths
        self.executable_filename    = f'job_condor__{self.current_tag}'
        self.condor_submit_filename = f'condor_submit__{self.current_tag}'

        if self.use_dag:
            self.dag_filename  = f'dag__{self.current_tag}.dag'
            self.dagfile       = f'{self.condor_output_path}/{self.dag_filename}'
        else:
            # name of executables and submits files
            self.executable_filename    = f'{self.executable_filename}'
            self.condor_submit_filename = f'{self.condor_submit_filename}'

            self.executable    = f'{self.condor_output_path}/{self.executable_filename}'
            self.condor_submit = f'{self.condor_output_path}/{self.condor_submit_filename}'


        self.dagfile_content = ''

        self.setup_contents()

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
    def setup_contents(self):
        with open(f'templates/job_condor_TEMPLATE.sh', 'r') as inf:
            self.content_sh = inf.read()
        with open(f'templates/condor_submit_TEMPLATE.sub', 'r') as inf:
            self.content_sub = inf.read()
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
    def create_scripts(self, extra_path='', extra_tag='', extra_cmds='', previous_sh_cmds='', setup_flags='',
                       reset_files=True):

        submits_logs_dir = self.condor_output_path
        
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
        
        executable    = f'{submits_logs_dir}/{executable_filename}'
        condor_submit = f'{submits_logs_dir}/{condor_submit_filename}'


        # path of the .sub from the .dag file
        rel_path_dag_submits = os.path.relpath(submits_logs_dir, self.condor_output_path)


        cmd_copy, cmd_delete = prepare_input_files(self.path_eos,
                                                   self.excluded_dirs,
                                                   self.include_dirs_list)


        setup_command = f'check_command_success source setup.sh'


        # modify actual command
        cmd = self.cmd
        if self.cpus:
            cmd += f' --cpus {self.cpus}'
        
        # ------------------------------------------------------------------------------------------
        # SHELL FILE
        # ------------------------------------------------------------------------------------------
        shell_filename = f'{submits_logs_dir}/{executable_filename}'

        replace_in_string(self.content_sh, shell_filename, [
            ('PREVIOUSCOMMANDS', previous_sh_cmds),
            ('SETUPCOMMAND'    , setup_command + setup_flags),
            ('COPYCOMMAND'     , cmd_copy),
            ('DELETEFILES'     , cmd_delete),
            ('CMD'             , f'{cmd} --copy_out_files {self.path_eos2 if self.path_eos2 else self.path_eos} {extra_cmds}')
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
    def reset_files(self):
        self.include_dirs_list.clear()
        self.excluded_dirs.clear()
        return
    # ==============================================================================================
    
    # ==============================================================================================
    def save_dag(self):
        with open(self.dagfile, 'w') as outdag:
            outdag.write(self.dagfile_content)
        return
    # ==============================================================================================
# ==================================================================================================


