import os, sys
import glob
import subprocess

jobflavours = [
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
def prepare_include_copy_cmd(input_path, output_path=None, source_dir=None):
    
    if not output_path and not source_dir:
        print(f'Error preparing to include directory {input_path}. You need to specify either the source dir' + \
              f' or the output path')
        raise ValueError

    cmds = []

    # when output_path is not specified, and source_dir is, the output will be inferred by removing
    # source_dir from input_path
    if source_dir and not output_path:

        include_dir_nosource = input_path.replace(source_dir+'/', '').rsplit('/', 1)[0]
        print(f'Adding included directory:  {input_path} ------> {include_dir_nosource}')

        cmds += [
            f'check_command_success mkdir -p {include_dir_nosource}',
            f'check_command_success cp -r {input_path} {include_dir_nosource}'
        ]
    
    elif output_path and not source_dir:

        print(f'Adding included directory:  {input_path} ------> {output_path}')

        cmds += [
            f'check_command_success mkdir -p {output_path}',
            f'check_command_success cp -r {input_path} {output_path}'
        ]

    print(f'Will do the following operations:')
    for c in cmds:
        print(f'  {c}')

    return cmds
#===================================================================================================

#===================================================================================================
def prepare_exclude_copy_cmd(source_dir, exclude_dirs):
    
    files_source_dir = glob.glob(f'{source_dir}/*')

    if 'exclude' in exclude_dirs:
        print(f'Will exclude the following directories')
        for d in exclude_dirs['exclude']:
            print(f'    {d}')


    cmds           = []
    excluded_files = []
    files_copy     = []
    files_delete   = []


    for f in files_source_dir:
        print(f'Processing directory {f}')
        # exclude directories
        
        if exclude_dirs['exclude']:
            print(f'Looping on directories/files to exclude:')
            for this_dir_exclude in exclude_dirs['exclude']:
                print(f'  Checking on {this_dir_exclude}')

                if this_dir_exclude.split('/', 1)[0] not in f:
                    print(f'    {this_dir_exclude} not present in {f}')
                    continue
                
                # count how many / are there in the exclude directory
                nslashes = this_dir_exclude.count('/')

                if nslashes == 0:
                    if this_dir_exclude in f:
                        print(f'    Excluding directory {this_dir_exclude}')
                        excluded_files.append(f)
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

    print(f'List of files/directories to copy')
    for this_file in files_copy:
        print(f'  {this_file}')


    for this_file in files_copy:
        cmds += create_parent_dirs(this_file, source_dir, '.')
    

    
    if files_delete:
        cmd_files_del = 'check_command_success rm ' + ' '.join(_f for _f in files_delete)
    else:
        cmd_files_del = ''


    print(f'Command to copy files:')
    for c in cmds:
        print(f'  {c}')
    
    print(f'Command to delete files:')
    print(f'  {cmd_files_del}')

    return cmds, cmd_files_del
#===================================================================================================

#===================================================================================================
def create_parent_dirs(obj, source, destination):

    check_cmd = 'check_command_success '
    relpath   = os.path.relpath(obj, source)
    cmds      = []

    # check whether the obj is a file or dir
    if os.path.isdir(obj):
        cmds.append(f'{check_cmd} mkdir -p {destination}/{relpath}')
        obj_final = os.path.dirname(f'{destination}/{relpath}')
        cmds.append(f'{check_cmd} cp -r {source}/{relpath} {obj_final}')
    
    elif os.path.isfile(obj):
        dirname                  = os.path.dirname(relpath)
        file_path_in_destination = f'{destination}/{dirname}'
        cmds.append(f'{check_cmd} mkdir -p {file_path_in_destination}')
        cmds.append(f'{check_cmd} cp -r {obj} {file_path_in_destination}')
    
    return cmds
#===================================================================================================

#===================================================================================================
def get_paths_file(infile):
    paths = []
    with open(infile, 'r') as f:
        lines = f.readlines()
    for l in lines:
        paths.append(l.strip('\n'))
    return paths
#===================================================================================================

