# Condor manager

This repository serves the porpouse of having a tool that automatically prepares to run scripts/code in condor.

At CERN/ATLAS, we have the afs shared filesystem, as well as the EOS space. However, new CERN accounts do not have the `work` afs storage, but only have afs for a maximum of 10GB.
This is not ideal for storing outputs of code. For this, I created this tool that automatically creates copies the input one needs for a particular job, runs it in condor, and then
the output is copied back. This is the ideal case when using EOS for storage, since we do not want to be using the EOS space whilst we run code in condor, since the performance
will decrease.

`condor_base` contains a class called `condor_manager`, which automatically will create the `.sub` and `.sh` files for the jobs.
The main core of the instructions of copying->running->copying back is inside the `.sh` file.
In case one wants, it is possible to use `DAGMAN` for the management of the condor jobs.

The script `prepare_sumits.py` is a template that one should follow with an example of how to use the class to prepare to run with condor.

## Instructions on how to use

We first need to define some paths:

- Outputs in `/eos/` (this could be a path that is synced with CERNBox for example)
- Second output path in `/eos/`, typically for mass storage (not synced to your computer)
- Path where submits files will be located, from the current-working-directory.

Create a dictionary with `local` and `remote` paths for outputs.

```python
path_results = {
    'local':  'this/output/path/for/local/storage',
    'remote':  'this/output/path/for/remote/storage',
}

```

Here this path is going to be passed to your script that you want to run as an argument, so that the script copies the output to `this/output/path`.

Initialize the `condor_manager` class. For this one needs to pass certain arguments:

- a tag which will uniquely define the job.
- flavour of the job. In the template the possible values are showed.
- the command that you want to execute to run the script.
- path to store the submit and executable files
- output paths. This is the dictionary `path_results` created previously
- output path in condor, that is, where to store outputs in condor before copying to `eos`.
- CPUs and RAM that you want the job to allocate.
- Whether to use dags or not
- Noitify, if you want to recieve the notification that the job finished.

Then it is possible to add paths to include when copying the files to condor, or to exclude some of them as well. In the template there's an example of how one should create this
dictionary. Then, once created, the scripts can be created by passing extra commands, extra paths, extra tags or commands to setup.
