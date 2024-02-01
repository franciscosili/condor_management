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
def prepare_input_files(source_dir, exclude_dirs=None, include_dirs=None):

    files_dir      = glob.glob(f'{source_dir}/*')
    files_cp       = []
    files_delete   = []
    files_excluded = []
    

    if exclude_dirs:
        print(f'Will exclude the following directories')
        for d in exclude_dirs:
            print(f'    {d}')
    
    for f in files_dir:
        print(f'Processing directory {f}')
        # exclude directories
        if exclude_dirs:
            
            print(f'  Looping on directories/files to exclude:')
            for this_dir_exclude in exclude_dirs:
                print(f'    Checking on {this_dir_exclude}')

                if this_dir_exclude.split('/', 1)[0] not in f:
                    print(f'      {this_dir_exclude} not present in {f}')
                    continue
                
                # count how many / are there in the exclude directory
                nslashes = this_dir_exclude.count('/')

                if nslashes == 0:
                    if this_dir_exclude in f:
                        print(f'      Excluding directory {this_dir_exclude}')
                        files_excluded.append(f)
                        continue
                else:
                    # we want to list all directories and files up to the depth given by the number of slashes
                    # for example: we want to exclude
                    #     dir1/subdir2/subsubdirA
                    #     dir2/subdir1/subsubdirB
                    # then we want to look for subdirectories recursively up to depth 2
                    files_up_to_depth = list_directories_up_to_depth(f, nslashes)
                    # now from the files obtain up to  certain depth, we want to exclude the ones
                    # that have already been excluded before
                    files_up_to_depth = [
                        _f for _f in files_up_to_depth \
                            if not (any(_d in _f for _d in files_excluded))
                    ]
                    
                    print(f'      Working on excluding {this_dir_exclude} which has a depth of {nslashes}')
                    print(f'      Files from the processed directory {f} up to depth {nslashes}:')
                    for _f in files_up_to_depth:
                        print(f'        {_f}')
                    

                    for subf in files_up_to_depth:
                        print(f'        Processing subdirectory {subf}')
                        if this_dir_exclude in subf:
                            print(f'          Excluding directory {this_dir_exclude}')
                            files_excluded.append(subf)
                            continue
                        if subf not in files_cp:
                            files_cp.append(subf)
                        
                        if os.path.isfile(f):
                            print(f'Will delete the following file after computing {f}')
                            files_delete.append(f.replace(f'{source_dir}/', ''))

        else:
            if f not in files_cp:
                files_cp.append(f)
        
        if os.path.isfile(f):
            files_delete.append(f.replace(f'{source_dir}/', ''))
    

    print(f'List of files/directories to copy')
    for this_file in files_cp:
        print(f'  {this_file}')


    cmd = ''
    for this_file in files_cp:
        cmd += create_parent_dirs(this_file, source_dir, '.')
        # # for all  files/dirs to copy, we need to get the relative path between the file and the source
        # # directory
        # relpath = os.path.relpath(this_file, source_dir)
        # if relpath != '.':
        #     # means it's not the same directory/file
        #     # for each file that we want to copy, we need to create the parent directory first
        #     if os.path.isdir(relpath):

            
        #     cmd += f'check_command_success mkdir -p {relpath}\n'
        #     cmd += f'check_command_success cp -r {source_dir}/{relpath} ./\n'
        # else:
        #     cmd += f'check_command_success cp -r {this_file} ./\n'

    # cmd = 'cp -r ' + ' '.join(f for f in files_cp) + ' ./\n'
    
    if include_dirs:
        for this_include_dir in include_dirs:
            if os.path.exists(this_include_dir):
                this_include_dir_nosource    = this_include_dir.replace(source_dir+'/', '')
                general_include_dir_nosource = this_include_dir_nosource.rsplit('/', 1)[0]

                cmd += f'check_command_success mkdir -p {general_include_dir_nosource}\n'
                cmd += f'check_command_success cp -r {this_include_dir} {general_include_dir_nosource}\n'
    
    if files_delete:
        cmd_files_del = 'check_command_success rm ' + ' '.join(_f for _f in files_delete)
    else:
        cmd_files_del = ''

    print(f'Command to copy files:')
    print(cmd)
    
    print(f'Command to delete files:')
    print(cmd_files_del)

    return cmd, cmd_files_del
#===================================================================================================

#===================================================================================================
def create_parent_dirs(obj, source, destination):

    check_cmd = 'check_command_success '

    # print(f'object with path {obj}')
    # print(f'source           {source}')
    # print(f'destination      {destination}')


    relpath = os.path.relpath(obj, source)
    # print(f'Relative path between object and source : {relpath}')


    cmd = ''


    # check whether the obj is a file or dir
    if os.path.isdir(obj):
        # print('object is a directory')

        # print(f'In the destination path, the obj will have the following path:')
        # print(f'    {destination}/{relpath}')

        cmd += f'{check_cmd} mkdir -p {destination}/{relpath}\n'

        # print(f'copying obj into the previous path')


        obj_final = os.path.dirname(f'{destination}/{relpath}')
        cmd += f'{check_cmd} cp -r {source}/{relpath} {obj_final}\n'
        # print(cmd)

        # os.system(cmd)
    
    elif os.path.isfile(obj):
        # print('object is a file')

        # print(f'In the destination path, the obj will have the following path:')
        # print(f'    {destination}/{relpath}')

        dirname = os.path.dirname(relpath)
        # print(f'Relative directory of the file: {dirname}')

        file_path_in_destination = f'{destination}/{dirname}'
        # print(f'file path in the destionation : {file_path_in_destination}')

        cmd += f'{check_cmd} mkdir -p {file_path_in_destination}\n'

        # print(f'copying obj into the destination path')


        cmd += f'{check_cmd} cp -r {obj} {file_path_in_destination}\n'
        # print(cmd)

        # os.system(cmd)
    return cmd
#===================================================================================================

