import os
import glob

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
        content = content.replace(*this_tuple)
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

# ==================================================================================================`
def prepare_input_files(source_dir, exclude_dirs=None, include_dirs=None):
    files_dir    = glob.glob(f'{source_dir}/*')
    files_cp     = []
    
    files_delete = []
    
    for f in files_dir:
        if exclude_dirs and any(exclude_dir in f for exclude_dir in exclude_dirs):
            continue
        files_cp.append(f)

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
    
    cmd_files_del = 'rm ' + ' '.join(_f for _f in files_delete)
    return cmd, cmd_files_del
# ==================================================================================================`

