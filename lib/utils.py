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


# ==================================================================================================`
def mkdirp(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path
# ==================================================================================================`

# ==================================================================================================`
def get_filename_path(filename):
    return os.path.dirname(filename)
# ==================================================================================================`

# ==================================================================================================`
def replace_in_string(input_str, output, replace_list_tuple):
    content = input_str
    for this_tuple in replace_list_tuple:
        content = content.replace(str(this_tuple[0]), str(this_tuple[1]))
    with open(output, 'w') as out:
        out.write(content)
    return
# ==================================================================================================`

# ==================================================================================================`
def get_template_content(templatefile):
    with open(templatefile, 'r') as inf:
        content = inf.read()
    return content
# ==================================================================================================`

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

# ==================================================================================================`
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
            for this_dir_exclude in exclude_dirs:
                print(f'Will try to exclude the following directory {this_dir_exclude}')

                # count how many / are there in the exclude directory
                nslashes = this_dir_exclude.count('/')

                if nslashes == 0:
                    if this_dir_exclude in f:
                        print(f'Excluding directory {this_dir_exclude}')
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

                    print(f'Trying to exclude {this_dir_exclude} which has a depth of {nslashes}')
                    print(f'Files from the processed directory up to depth {nslashes}')
                    for _f in files_up_to_depth:
                        print(f'    {_f}')

                    for subf in files_up_to_depth:
                        print(f'Processing subdirectory {subf}')
                        if this_dir_exclude in subf:
                            print(f'Excluding directory {this_dir_exclude}')
                            continue
                        files_cp.append(subf)
                        
                        if os.path.isfile(f):
                            print(f'Will delete the following file after computing {f}')
                            files_delete.append(f.replace(f'{source_dir}/', ''))
                    

        # if exclude_dirs and any(exclude_dir in f for exclude_dir in exclude_dirs):
        #     continue
        # files_cp.append(f)

        if os.path.isfile(f):
            files_delete.append(f.replace(f'{source_dir}/', ''))
        
    cmd = 'cp -r ' + ' '.join(f for f in files_cp) + ' ./\n'
    
    if include_dirs:
        for this_include_dir in include_dirs:
            if os.path.exists(this_include_dir):
                this_include_dir_nosource    = this_include_dir.replace(source_dir+'/', '')
                general_include_dir_nosource = this_include_dir_nosource.rsplit('/', 1)[0]

                cmd += f'mkdir -p {general_include_dir_nosource}\n'
                cmd += f'cp -r {this_include_dir} {general_include_dir_nosource}\n'
    
    if files_delete:
        cmd_files_del = 'check_command_success rm ' + ' '.join(_f for _f in files_delete)
    else:
        cmd_files_del = ''

    return cmd, cmd_files_del
# ==================================================================================================`

