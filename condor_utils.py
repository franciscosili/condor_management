import os
import glob
import re
import sys
from subprocess import run
from pathlib import Path
from contextlib import chdir

JOBFLAVOURS: list[str] = [
    'espresso',     # 20 minutes
    'microcentury', # 1 hour
    'longlunch',    # 2 hours
    'workday',      # 8 hours
    'tomorrow',     # 1 day
    'testmatch',    # 3 days
    'nextweek',     # 1 week
]


#===================================================================================================
def mkdirp(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path
#===================================================================================================

#===================================================================================================
def get_filename_path(filename):
    return os.path.dirname(filename)
#===================================================================================================

#===================================================================================================
def replace_in_string(input_str, output, replace_list_tuple):
    content = input_str
    for this_tuple in replace_list_tuple:
        content = content.replace(str(this_tuple[0]), str(this_tuple[1]))
    
    print(f'------- CREATING FILE {output}')
    with open(output, 'w') as out:
        out.write(content)
    return
#===================================================================================================

#===================================================================================================
def get_template_content(templatefile):
    with open(templatefile, 'r') as inf:
        content = inf.read()
    return content
#===================================================================================================

#===================================================================================================
def list_directories_up_to_depth(root_dir, depth):
    directories   = []
    current_depth = 0

    while current_depth <= depth:
        pattern = f"{root_dir}/*" * current_depth
        subdirectories = glob.glob(pattern)
        directories.extend(subdirectories)
        current_depth += 1

    return directories
#===================================================================================================

#===================================================================================================
def prepare_include_copy_cmd(input_path: str, output_path: str) -> list[str]:
    
    cmds: list[str] = []

    print(f'Adding included directory:  {input_path} ------> {output_path}')

    cmds += [
        f'check_command_success mkdir -p {output_path}',
        f'check_command_success rsync -a --exclude="*/*.pdf" --exclude="*/macros" {input_path} {output_path}'
    ]

    print('Will do the following operations:')
    for c in cmds:
        print(f'  {c}')

    return cmds
#===================================================================================================

#===================================================================================================
def prepare_exclude_copy_cmd(source_dir: str, exclude_dirs: list[str]) -> tuple[list[str], str]:
    
    files_source_dir: list[str] = glob.glob(f'{source_dir}/*')

    print(files_source_dir)
    
    print('Will exclude the following directories')
    for d in exclude_dirs:
        print(f'    {d}')
    

    cmds          : list[str] = []
    excluded_files: list[str] = []
    files_copy    : list[str] = []
    files_delete  : list[str] = []


    for f in files_source_dir:
        print(f'Processing directory {f}')
        # exclude directories
        
        if any(f in f'{source_dir}/{exclude}' for exclude in exclude_dirs):
            print('Looping on directories/files to exclude:')
            for this_dir_exclude in exclude_dirs:
                print(f'  Checking on {this_dir_exclude}')

                if this_dir_exclude.split('/', 1)[0] not in f:
                    print(f'    {this_dir_exclude} not present in {f}')
                    continue
                
                # count how many / are there in the exclude directory
                nslashes: int = this_dir_exclude.count('/')

                if nslashes == 0:
                    if this_dir_exclude in f:
                        print(f'    Excluding directory {this_dir_exclude}')
                        excluded_files.append(f)
                        continue
                    else:
                        files_copy.append(f)
                        continue

                else:
                    # we want to list all directories and files up to the depth given by the number of slashes
                    # for example: we want to exclude
                    #     dir1/subdir2/subsubdirA
                    #     dir2/subdir1/subsubdirB
                    # then we want to look for subdirectories recursively up to depth 2
                    files_up_to_depth = list_directories_up_to_depth(f, nslashes)
                    # now from the files obtained up to certain depth, we want to exclude the ones
                    # that have already been excluded before
                    files_up_to_depth = [
                        _f for _f in files_up_to_depth \
                            if not (any(_d in _f for _d in excluded_files))
                    ]
                    
                    print(f'    Working on excluding {this_dir_exclude} which has a depth of {nslashes}')
                    print(f'    Files from the processed directory {f} up to depth {nslashes}:')
                    for _f in files_up_to_depth:
                        print(f'      {_f}')
                    

                    for subf in files_up_to_depth:
                        print(f'      Processing subdirectory {subf}')
                        if this_dir_exclude in subf:
                            print(f'        Excluding directory {this_dir_exclude}')
                            excluded_files.append(subf)
                            continue
                            
                        if subf in excluded_files:
                            print(f'        Skipping already excluded directory {this_dir_exclude}')
                            continue
                        
                        if subf not in files_copy:
                            files_copy.append(subf)
                        
                        if os.path.isfile(f):
                            print(f'Will delete the following file after computing {f}')
                            files_delete.append(f.replace(f'{source_dir}/', ''))

        else:
            if f not in files_copy:
                print(f'Adding {f} to files to be copied')
                files_copy.append(f)
        
        if os.path.isfile(f):
            file_del = f.replace(f'{source_dir}/', '')
            print(f'Will remove this file after: {file_del}')
            files_delete.append(file_del)
    

    files_copy = [f for f in files_copy if f not in excluded_files]

    print('List of files/directories to copy')
    for this_file in files_copy:
        print(f'  {this_file}')


    for this_file in files_copy:
        cmds += create_parent_dirs(this_file, source_dir, '.')
    
    
    if files_delete:
        cmd_files_del: str = 'check_command_success rm ' + ' '.join(_f for _f in files_delete)
    else:
        cmd_files_del: str = ''


    print('Command to copy files:')
    for c in cmds:
        print(f'  {c}')
    
    print('Command to delete files:')
    print(f'  {cmd_files_del}')

    return cmds, cmd_files_del
#===================================================================================================

#===================================================================================================
def create_parent_dirs(obj: str, source: str, destination: str) -> list[str]:

    check_cmd: str = 'check_command_success'
    relpath  : str = os.path.relpath(obj, source)
    cmds     : list[str] = []

    # check whether the obj is a file or dir
    if os.path.isdir(obj):
        cmds.append(f'{check_cmd} mkdir -p {destination}/{relpath}')
        obj_final: str = os.path.dirname(f'{destination}/{relpath}')
        cmds.append(f'{check_cmd} cp -r {source}/{relpath} {obj_final}')
    
    elif os.path.isfile(obj):
        dirname                 : str = os.path.dirname(relpath)
        file_path_in_destination: str = f'{destination}/{dirname}'
        cmds.append(f'{check_cmd} mkdir -p {file_path_in_destination}')
        cmds.append(f'{check_cmd} cp -r {obj} {file_path_in_destination}')
    
    return cmds
#===================================================================================================

#===================================================================================================
def get_paths_file(infile):
    paths = []
    with open(infile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        paths.append(line.strip('\n'))
    return paths
#===================================================================================================




#===================================================================================================
#===================================================================================================
#===================================================================================================
# helper function to copy output directory from each script to eos
#===================================================================================================
#===================================================================================================
#===================================================================================================

#==================================================================================================
def copy_dir(input_path, output_path) -> None:
    """function to copy a directory from one path to another
    """
    import shutil
    mkdirp(output_path)
    
    print(f'Copying directory: {input_path} -----> {output_path}')
    shutil.copytree(input_path, output_path, dirs_exist_ok=True)
    return
#==================================================================================================

#===================================================================================================
def copy_output_from_condor(condor_path : str,
                            output_path : str) -> None:
    
    # delete the ./ and remote directories in case it exist
    print(f'Results path in condor: {condor_path}')

    condor_path = condor_path.strip('./')
    common_path = condor_path.replace('remote/', '')
    # common_path is the path that will exist in eos
    
    # now we need to create the common_path in the output_path
    output_common_path = f'{output_path}/{common_path}'

    print(f'Creating common path in /eos/: {output_common_path}')
    mkdirp(output_common_path)

    print('Looping inside the common path and copying directories to eos')
    copy_dir(f'{condor_path}', output_common_path)
    return
#===================================================================================================